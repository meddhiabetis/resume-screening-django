#!/bin/bash

# Define the project structure
directories=(
    "requirements"
    "core"
    "core/settings"
    "apps"
    "apps/accounts"
    "apps/accounts/templates"
    "apps/accounts/templates/accounts"
    "apps/resume_analysis"
    "apps/resume_analysis/views"
    "apps/resume_analysis/services"
    "apps/resume_analysis/templates"
    "apps/resume_analysis/templates/resume_analysis"
    "apps/chatbot"
    "static"
    "static/css"
    "static/js"
    "static/images"
    "templates"
    "media"
    "media/resumes"
    "utils"
)

files=(
    ".env"
    ".gitignore"
    "README.md"
    "requirements/base.txt"
    "requirements/dev.txt"
    "requirements/prod.txt"
    "manage.py"
    "core/__init__.py"
    "core/settings/__init__.py"
    "core/settings/base.py"
    "core/settings/dev.py"
    "core/settings/prod.py"
    "core/urls.py"
    "core/wsgi.py"
    "core/asgi.py"
    "apps/accounts/__init__.py"
    "apps/accounts/admin.py"
    "apps/accounts/apps.py"
    "apps/accounts/forms.py"
    "apps/accounts/models.py"
    "apps/accounts/urls.py"
    "apps/accounts/views.py"
    "apps/accounts/templates/accounts/login.html"
    "apps/accounts/templates/accounts/register.html"
    "apps/accounts/templates/accounts/profile.html"
    "apps/resume_analysis/__init__.py"
    "apps/resume_analysis/admin.py"
    "apps/resume_analysis/apps.py"
    "apps/resume_analysis/forms.py"
    "apps/resume_analysis/models.py"
    "apps/resume_analysis/urls.py"
    "apps/resume_analysis/views/__init__.py"
    "apps/resume_analysis/views/analysis.py"
    "apps/resume_analysis/views/dashboard.py"
    "apps/resume_analysis/services/__init__.py"
    "apps/resume_analysis/services/llm_service.py"
    "apps/resume_analysis/services/pdf_service.py"
    "apps/resume_analysis/services/analysis_service.py"
    "apps/resume_analysis/templates/resume_analysis/dashboard.html"
    "apps/resume_analysis/templates/resume_analysis/single_analysis.html"
    "apps/resume_analysis/templates/resume_analysis/multiple_analysis.html"
    "apps/chatbot/__init__.py"
    "templates/base.html"
    "templates/navbar.html"
    "templates/footer.html"
    "utils/__init__.py"
    "utils/constants.py"
    "utils/helpers.py"
)

# Create directories
for dir in "${directories[@]}"; do
    mkdir -p "$dir"
done

# Create empty files
for file in "${files[@]}"; do
    touch "$file"
done

echo "Project structure created successfully!"
