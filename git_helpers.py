import os
import base64
from github import Github, InputGitAuthor

GITHUB_TOKEN = os.environ.get("PAT_TOKEN") 
REPO_NAME = "benhm1/benhm1.github.io"

REPO = Github(GITHUB_TOKEN).get_repo(REPO_NAME)

def update_readme(train_num):

    contents = REPO.get_contents('README.md')

    readme_content = contents.decoded_content.decode('utf-8')
    
    trains = readme_content.split('\n')

    new_train = f'* [Train {train_num}](train_{train_num}.md)'

    if new_train in trains:
        print('Train is already there!')
        return
    
    trains.append(new_train)

    trains.sort()

    REPO.update_file(
        path='README.md',
        message=f'Adding {train_num} to TOC',
        content='\n'.join(trains), 
        sha=contents.sha
    )

    print("Readme updated")
    

def get_file_contents(file_path):
    
    try:
        contents = REPO.get_contents(file_path)
    
    except Exception as e:
        if "404" in str(e):
            print(f"File '{file_path}' does not exist.")
        else:
            print(f"An unexpected error occurred: {e}")
        return None
    
    return contents
    
    
def push_file(file_path, file_content, commit_message):
    
    created = False
    
    existing = get_file_contents(file_path)
    
    if existing is None:
        REPO.create_file(
            path=file_path, 
            message=commit_message, 
            content=file_content
        )
        print("File created successfully.")
        created = True
    else:
        REPO.update_file(
            path=file_path, 
            message=commit_message, 
            content=file_content, 
            sha=existing.sha
        )
        print("File updated successfully.")
    return created
