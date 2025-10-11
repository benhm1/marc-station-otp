import os
import base64
from github import Github, InputGitAuthor

GITHUB_TOKEN = os.environ.get("PAT_TOKEN") 
REPO_NAME = "benhm1/benhm1.github.io"

def update_readme(train_num):

    g = Github(GITHUB_TOKEN)
    try:
        # Get the repository object
        repo = g.get_repo(REPO_NAME)
    except Exception as e:
        print(f"Error getting repository: {e}")
        return None

    contents = repo.get_contents('README.md')

    readme_content = contents.decoded_content.decode('utf-8')
    
    trains = readme_content.split('\n')

    new_train = f'* [Train {train_num}]({train_num}.md)'

    if new_train in trains:
        print('Train is already there!')
        return
    
    trains.append(new_train)

    trains.sort()

    repo.update_file(
        path='README.md',
        message=f'Adding {train_num} to TOC',
        content='\n'.join(trains), 
        sha=contents.sha
    )

    print("Readme updated")
    

def get_file_contents(file_path):
    g = Github(GITHUB_TOKEN)
    try:
        # Get the repository object
        repo = g.get_repo(REPO_NAME)
    except Exception as e:
        print(f"Error getting repository: {e}")
        return None

    try:
        # Check if the file already exists in the repo
        contents = repo.get_contents(file_path)
    
    except Exception as e:
        # If the file does NOT exist (raises an exception), create it
        if "404" in str(e):
            print(f"File '{file_path}' does not exist.")
        else:
            print(f"An unexpected error occurred: {e}")
        return None
    
    return contents
    
    
def push_file_to_github(file_path, file_content, commit_message):
    """Pushes a file with in-memory content to a GitHub repository."""
    
    created = False
    existing = get_file_contents(file_path)
    if existing is None:
        repo.create_file(
            path=file_path, 
            message=commit_message, 
            content=file_content
        )
        print("File created successfully.")
        created = True
    else:
        repo.update_file(
            path=file_path, 
            message=commit_message, 
            content=file_content, 
            sha=contents.sha
        )
        print("File updated successfully.")
    return created
