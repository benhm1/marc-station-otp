import os
import base64
from github import Github, InputGitAuthor

GITHUB_TOKEN = os.environ.get("PAT_TOKEN") 
REPO_NAME = "benhm1/benhm1.github.io"

def update_readme(repo, train_num):
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
    

def push_file_to_github(train_num, file_path, file_content, commit_message):
    """Pushes a file with in-memory content to a GitHub repository."""
    
    g = Github(GITHUB_TOKEN)
    try:
        # Get the repository object
        repo = g.get_repo(REPO_NAME)
    except Exception as e:
        print(f"Error getting repository: {e}")
        return

    try:
        # Check if the file already exists in the repo
        contents = repo.get_contents(file_path)
        
        # If the file exists, update it
        print(f"File '{file_path}' exists. Updating content...")
        
        # The update_file method handles converting the string/bytes to base64
        repo.update_file(
            path=file_path, 
            message=commit_message, 
            content=file_content, 
            sha=contents.sha
        )
        print("File updated successfully.")

    except Exception as e:
        # If the file does NOT exist (raises an exception), create it
        if "404" in str(e): 
            print(f"File '{file_path}' does not exist. Creating new file...")
            
            # The create_file method handles converting the string/bytes to base64
            repo.create_file(
                path=file_path, 
                message=commit_message, 
                content=file_content
            )
            print("File created successfully.")

            update_readme(repo, train_num)
        else:
            print(f"An unexpected error occurred: {e}")

