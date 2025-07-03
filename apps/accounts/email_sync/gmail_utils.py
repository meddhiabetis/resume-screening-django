import os
from base64 import urlsafe_b64decode
from email import message_from_bytes
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.tiff', '.bmp']

def fetch_gmail_pdfs(access_token, gmail_email, before, after, save_dir, subject=None):
    """
    Fetch all allowed attachment types (.pdf, .doc, .docx, images) from Gmail within the date range.

    Args:
        access_token (str): OAuth 2.0 access token for Gmail API.
        gmail_email (str): The email address of the Gmail account.
        before (str): The date before which to search for emails (YYYY/MM/DD).
        after (str): The date after which to search for emails (YYYY/MM/DD).
        save_dir (str): Directory where the attachments will be saved.
        subject (str, optional): Subject filter for the emails. Defaults to None.

    Returns:
        list: A list of saved file paths for the downloaded attachments.
    """
    try:
        creds = Credentials(token=access_token)
        service = build('gmail', 'v1', credentials=creds)
        # Compose Gmail search query
        query = f"after:{after} before:{before} has:attachment"
        if subject:
            query += f' subject:"{subject}"'
        results = service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])
        if not messages:
            return []

        saved_files = []
        for msg in messages:
            msg_id = msg['id']
            msg_data = service.users().messages().get(userId='me', id=msg_id, format='raw').execute()
            raw_msg = urlsafe_b64decode(msg_data['raw'].encode('ASCII'))
            email_msg = message_from_bytes(raw_msg)

            for part in email_msg.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                filename = part.get_filename()
                if filename:
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in ALLOWED_EXTENSIONS:
                        # Ensure filename is unique
                        safe_filename = filename
                        counter = 1
                        while os.path.exists(os.path.join(save_dir, safe_filename)):
                            name, extension = os.path.splitext(filename)
                            safe_filename = f"{name}_{counter}{extension}"
                            counter += 1
                        file_path = os.path.join(save_dir, safe_filename)
                        with open(file_path, 'wb') as f:
                            f.write(part.get_payload(decode=True))
                        saved_files.append(file_path)
        return saved_files
    except HttpError as error:
        print(f'An error occurred: {error}')
        return []