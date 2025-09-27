import os
import json
import logging
import re
from typing import Any, Dict, List

import requests
from django.conf import settings
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


class MistralLLMQueryService:
    """
    LLM-assisted query planner using Mistral.
    - Enhance query (extract entities)
    - Execute a safe, deterministic read-only Cypher that we build
    """

    def __init__(self, model: str = "mistral-small-latest", timeout: float = 12.0):
        self.api_key = os.getenv("MISTRAL_API_KEY", "")
        self.model = model
        self.timeout = timeout
        # Neo4j settings
        self.neo4j_uri = getattr(settings, "NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = getattr(settings, "NEO4J_USER", "neo4j")
        self.neo4j_password = getattr(settings, "NEO4J_PASSWORD", "your-password")

        # Whitelists to prevent malicious Cypher (for LLM-provided Cypher only)
        self.allowed_labels = {"Resume", "Skill", "Title", "Company", "School"}
        self.allowed_rels = {"HAS_SKILL", "HAS_TITLE", "WORKED_AT", "STUDIED_AT"}

        # Block write/side-effect statements
        self.blocked_keywords = {"CREATE", "MERGE", "DELETE", "SET", "REMOVE", "CALL", "LOAD", "APOC", "FOREACH"}

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def enhance_query(self, user_query: str, limit: int = 10) -> Dict[str, Any]:
        """
        Return JSON plan with normalized arrays:
        { skills, titles, companies, schools, orgs, cypher }
        """
        if not self.enabled or not user_query:
            return {"skills": [], "titles": [], "companies": [], "schools": [], "orgs": [], "cypher": ""}

        system = (
            "You are a query planner for a resume graph search. "
            "Return a STRICT JSON object only. No commentary. No code fences. "
            "Graph schema: Nodes: Resume(id, file_name), Skill(name), Title(name), Company(name), School(name). "
            "Relationships: (Resume)-[:HAS_SKILL]->(Skill), (Resume)-[:HAS_TITLE]->(Title), "
            "(Resume)-[:WORKED_AT]->(Company), (Resume)-[:STUDIED_AT]->(School). "
            "Task: Extract arrays for skills, titles, companies, schools (lowercase)."
        )
        user = f"User query: {user_query}\nReturn JSON with keys: skills, titles, companies, schools, orgs, cypher."

        try:
            content = self._call_mistral_chat(system, user)
            plan = self._safe_parse_json(content)
            plan = plan if isinstance(plan, dict) else {}
            for k in ["skills", "titles", "companies", "schools", "orgs"]:
                plan.setdefault(k, [])
                if not isinstance(plan[k], list):
                    plan[k] = []
                plan[k] = [str(x).strip().lower() for x in plan[k] if isinstance(x, (str, int, float))]
            if not isinstance(plan.get("cypher", ""), str):
                plan["cypher"] = ""
            return plan
        except Exception as e:
            logger.warning(f"Mistral enhance_query failed: {e}")
            return {"skills": [], "titles": [], "companies": [], "schools": [], "orgs": [], "cypher": ""}

    def build_readonly_cypher_v3(self) -> str:
        """
        Weighted scoring with softened gates:
        Final score = sum(normalized_weight(category) * ratio(category))
        - skills ratio = (matched required skills / total required skills) * skill_strength (avg rel.confidence)
        - titles ratio = matched req titles / total req titles
        - companies ratio = matched req companies / total req companies (substring match)
        - schools ratio = matched req schools / total req schools (substring match)
        Weights are normalized over requested categories to sum to 1.
        Returns only related items for display.
        """
        return """
        MATCH (r:Resume)

        // Skills
        OPTIONAL MATCH (r)-[hs:HAS_SKILL]->(s:Skill)
        WHERE $req_skills <> [] AND s.name IN $req_skills
        WITH r,
             collect(DISTINCT s.name) as matched_skills,
             CASE WHEN count(hs)=0 THEN 1.0 ELSE avg(COALESCE(hs.confidence, 1.0)) END as avg_conf,
             $req_skills as req_skills,
             $req_titles as req_titles,
             $req_companies as req_companies,
             $req_schools as req_schools,
             toFloat($w_skills) as wS, toFloat($w_titles) as wT, toFloat($w_companies) as wC, toFloat($w_schools) as wU

        // Titles
        OPTIONAL MATCH (r)-[:HAS_TITLE]->(t:Title)
        WITH r, matched_skills, avg_conf, req_skills, req_titles, req_companies, req_schools, wS,wT,wC,wU,
             collect(DISTINCT t.name) as titles_all

        // Companies
        OPTIONAL MATCH (r)-[:WORKED_AT]->(c:Company)
        WITH r, matched_skills, avg_conf, titles_all, req_skills, req_titles, req_companies, req_schools, wS,wT,wC,wU,
             collect(DISTINCT c.name) as companies_all

        // Schools
        OPTIONAL MATCH (r)-[:STUDIED_AT]->(sch:School)
        WITH r, matched_skills, avg_conf, titles_all, companies_all, req_skills, req_titles, req_companies, req_schools, wS,wT,wC,wU,
             collect(DISTINCT sch.name) as schools_all

        // Derive matched required items and display sets
        WITH r, matched_skills, avg_conf,
             [rt IN req_titles WHERE rt IN titles_all] as matched_titles_req,
             [rc IN req_companies WHERE any(c IN companies_all WHERE c CONTAINS rc OR rc CONTAINS c)] as matched_req_companies,
             [rs IN req_schools WHERE any(s IN schools_all WHERE s CONTAINS rs OR rs CONTAINS s)] as matched_req_schools,
             [c IN companies_all WHERE any(rc IN req_companies WHERE c CONTAINS rc OR rc CONTAINS c)] as matched_companies,
             [s IN schools_all   WHERE any(rs IN req_schools  WHERE s CONTAINS rs OR rs CONTAINS s)] as matched_schools,
             req_skills, req_titles, req_companies, req_schools, wS,wT,wC,wU

        // Counts and totals
        WITH r, matched_skills, matched_titles_req, matched_companies, matched_schools, avg_conf,
             size(matched_skills) as skills_hit,
             size(req_skills) as skills_total,
             size(matched_titles_req) as titles_hit,
             size(req_titles) as titles_total,
             size(matched_req_companies) as companies_hit,
             size(req_companies) as companies_total,
             size(matched_req_schools) as schools_hit,
             size(req_schools) as schools_total,
             wS,wT,wC,wU

        // Ratios
        WITH r, matched_skills, matched_titles_req as matched_titles, matched_companies, matched_schools,
             skills_hit, skills_total, titles_hit, titles_total, companies_hit, companies_total, schools_hit, schools_total,
             (CASE WHEN skills_total=0 THEN 0.0 ELSE toFloat(skills_hit)/toFloat(skills_total) END) as skills_ratio_raw,
             COALESCE(avg_conf, 1.0) as skill_strength,
             (CASE WHEN titles_total=0 THEN 0.0 ELSE toFloat(titles_hit)/toFloat(titles_total) END) as titles_ratio,
             (CASE WHEN companies_total=0 THEN 0.0 ELSE toFloat(companies_hit)/toFloat(companies_total) END) as companies_ratio,
             (CASE WHEN schools_total=0 THEN 0.0 ELSE toFloat(schools_hit)/toFloat(schools_total) END) as schools_ratio,
             wS,wT,wC,wU

        // Apply skill strength
        WITH r, matched_skills, matched_titles, matched_companies, matched_schools,
             skills_hit, skills_total, titles_hit, titles_total, companies_hit, companies_total, schools_hit, schools_total,
             (skills_ratio_raw * skill_strength) as skills_ratio,
             titles_ratio, companies_ratio, schools_ratio,
             wS,wT,wC,wU, skill_strength

        // Normalize weights over requested categories
        WITH r, matched_skills, matched_titles, matched_companies, matched_schools,
             skills_hit, skills_total, titles_hit, titles_total, companies_hit, companies_total, schools_hit, schools_total,
             skills_ratio, titles_ratio, companies_ratio, schools_ratio, skill_strength,
             (CASE WHEN skills_total>0 THEN wS ELSE 0 END +
              CASE WHEN titles_total>0 THEN wT ELSE 0 END +
              CASE WHEN companies_total>0 THEN wC ELSE 0 END +
              CASE WHEN schools_total>0 THEN wU ELSE 0 END) as w_sum,
             wS,wT,wC,wU

        WITH r, matched_skills, matched_titles, matched_companies, matched_schools,
             skills_hit, skills_total, titles_hit, titles_total, companies_hit, companies_total, schools_hit, schools_total,
             skills_ratio, titles_ratio, companies_ratio, schools_ratio, skill_strength,
             CASE WHEN w_sum=0 THEN 0 ELSE (CASE WHEN skills_total>0 THEN wS/w_sum ELSE 0 END) END as w_skills_norm,
             CASE WHEN w_sum=0 THEN 0 ELSE (CASE WHEN titles_total>0 THEN wT/w_sum ELSE 0 END) END as w_titles_norm,
             CASE WHEN w_sum=0 THEN 0 ELSE (CASE WHEN companies_total>0 THEN wC/w_sum ELSE 0 END) END as w_companies_norm,
             CASE WHEN w_sum=0 THEN 0 ELSE (CASE WHEN schools_total>0 THEN wU/w_sum ELSE 0 END) END as w_schools_norm

        WITH r, matched_skills, matched_titles, matched_companies, matched_schools,
             skills_hit, skills_total, titles_hit, titles_total, companies_hit, companies_total, schools_hit, schools_total,
             skills_ratio, titles_ratio, companies_ratio, schools_ratio, skill_strength,
             w_skills_norm, w_titles_norm, w_companies_norm, w_schools_norm,
             (skills_ratio*w_skills_norm + titles_ratio*w_titles_norm + companies_ratio*w_companies_norm + schools_ratio*w_schools_norm) as similarity_score

        RETURN r.id as resume_id,
               r.file_name as file_name,
               similarity_score,
               matched_skills as shared_skills,
               matched_titles as matched_titles,
               matched_companies as matched_companies,
               matched_schools as matched_schools,
               skills_hit, skills_total,
               titles_hit, titles_total,
               companies_hit, companies_total,
               schools_hit, schools_total,
               skill_strength,
               w_skills_norm, w_titles_norm, w_companies_norm, w_schools_norm
        ORDER BY similarity_score DESC
        LIMIT $limit
        """

    def run_builder_cypher(self, cypher: str, params: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Execute our known-good builder Cypher (skip LLM safety checks).
        """
        if not cypher or "RETURN" not in cypher or "resume_id" not in cypher:
            logger.warning("Builder Cypher missing required RETURN fields")
            return []

        params = dict(params or {})
        params.setdefault("limit", limit)

        driver = None
        try:
            driver = GraphDatabase.driver(self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_password))
            with driver.session() as session:
                result = session.run(cypher, **params)
                rows = []
                for record in result:
                    rows.append({
                        "resume_id": record.get("resume_id"),
                        "file_name": record.get("file_name"),
                        "similarity_score": float(record.get("similarity_score") or 0.0),
                        "shared_skills": list(record.get("shared_skills") or []),
                        "matched_titles": list(record.get("matched_titles") or []),
                        "matched_companies": list(record.get("matched_companies") or []),
                        "matched_schools": list(record.get("matched_schools") or []),
                        "skills_hit": int(record.get("skills_hit") or 0),
                        "skills_total": int(record.get("skills_total") or 0),
                        "titles_hit": int(record.get("titles_hit") or 0),
                        "titles_total": int(record.get("titles_total") or 0),
                        "companies_hit": int(record.get("companies_hit") or 0),
                        "companies_total": int(record.get("companies_total") or 0),
                        "schools_hit": int(record.get("schools_hit") or 0),
                        "schools_total": int(record.get("schools_total") or 0),
                        "skill_strength": float(record.get("skill_strength") or 1.0),
                        "w_skills_norm": float(record.get("w_skills_norm") or 0.0),
                        "w_titles_norm": float(record.get("w_titles_norm") or 0.0),
                        "w_companies_norm": float(record.get("w_companies_norm") or 0.0),
                        "w_schools_norm": float(record.get("w_schools_norm") or 0.0),
                    })
                return rows
        except Exception as e:
            logger.warning(f"Builder Cypher execution failed: {e}")
            return []
        finally:
            if driver:
                driver.close()

    # Optional: keep for diagnostics if you ever want to test LLM-provided Cypher.
    def run_cypher_readonly(self, cypher: str, params: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        if not cypher or not isinstance(cypher, str):
            return []
        cypher = self._normalize_cypher(cypher)
        if not self._is_cypher_safe(cypher):
            logger.warning("Blocked unsafe Cypher")
            return []
        return self.run_builder_cypher(cypher, params, limit)

    def _call_mistral_chat(self, system: str, user: str) -> str:
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.2,
            "max_tokens": 600,
        }
        resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _safe_parse_json(self, content: str) -> Dict[str, Any]:
        stripped = content.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```[a-zA-Z0-9]*\s*", "", stripped)
            stripped = re.sub(r"\s*```$", "", stripped)
        return json.loads(stripped)

    def _normalize_cypher(self, cypher: str) -> str:
        return re.sub(r"\bLET\b", "WITH", cypher, flags=re.IGNORECASE)

    def _is_cypher_safe(self, cypher: str) -> bool:
        upper = cypher.upper()
        if any(k in upper for k in self.blocked_keywords):
            return False
        label_matches = re.findall(r"\([a-zA-Z_][a-zA-Z0-9_]*\s*:(`?)([A-Za-z][A-Za-z0-9_]*)\1", cypher)
        for _, lab in label_matches:
            if lab not in self.allowed_labels:
                logger.warning(f"Blocked due to unknown label: {lab}")
                return False
        rel_matches = re.findall(r":(`?)([A-Z_]+)\1\]", cypher)
        for _, rel in rel_matches:
            if rel not in self.allowed_rels:
                logger.warning(f"Blocked due to unknown relationship: {rel}")
                return False
        if "RETURN" not in upper or "resume_id" not in cypher:
            return False
        return True