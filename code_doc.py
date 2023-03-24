import os
import argparse
import base64
from github import Github, UnknownObjectException, GithubException
import openai
import re

def revert_last_commit(repo):
    # Get the default branch
    default_branch = repo.default_branch
    
    # Retrieve the latest commit
    latest_commit = repo.get_branch(default_branch).commit

    # Identify the commit before the latest one
    previous_commit = latest_commit.parents[0]

    # Get the tree of the previous commit
    previous_tree = previous_commit.commit.tree

    # Create a new commit that reverts the changes made by the latest commit
    message = f"Revert: {latest_commit.commit.message}"
    #author = latest_commit.commit.author
    #repo.create_git_commit(message, previous_tree, [latest_commit.commit], author)
    repo.create_git_commit(message, previous_tree, [latest_commit.commit])

    # Update the default branch to point to the new commit
    repo.get_git_ref(f"heads/{default_branch}").edit(previous_commit.sha, force=True)

# Function to generate README using GPT-3
def generate_readme_gpt4(repo_name):
    # Implement GPT-3 integration and prompt for README generation
    # You should customize the prompt based on your requirements
    prompt = f"Create a detailed README for a GitHub repository named {repo_name}."
    
    response = openai.Completion.create(
        engine="text-davinci-002",  # Use the appropriate GPT-3 engine
        prompt=prompt,
        max_tokens=150,
        n=1,
        stop=None,
        temperature=0.5,
    )
    
    generated_text = response.choices[0].text.strip()
    
    # Call GPT-3 API and return the generated text
    return generated_text

# Function to add comments to files using GPT-4
import openai
import re

def add_comments_gpt4(file_content):
    # Define a pattern to match Terraform blocks
    block_pattern = re.compile(r'(?P<indent>\s*)(?P<block>resource|module|provider|variable|locals|data|output)', re.MULTILINE)

    # Function to call GPT-3 API and return the generated comment
    def generate_comment(block):
        prompt = f"Describe the purpose of the following Terraform code block:\n{block}"
        response = openai.Completion.create(
            engine="text-davinci-002",  # Use the appropriate GPT-3 engine
            prompt=prompt,
            max_tokens=50,
            n=1,
            stop=None,
            temperature=0.5,
        )
        return response.choices[0].text.strip()

    # Iterate through the file content, find Terraform blocks, and add comments
    position = 0
    updated_file_content = ""
    for match in block_pattern.finditer(file_content):
        # Add content before the code block
        updated_file_content += file_content[position:match.start()]
        
        # Add a comment above the code block
        comment = generate_comment(match.group('block'))
        updated_file_content += f"{match.group('indent')}# {comment}\n"
        
        # Add the code block
        updated_file_content += file_content[match.start():match.end()]
        
        # Update the position
        position = match.end()

    # Add the remaining content after the last code block
    updated_file_content += file_content[position:]

    return updated_file_content

# Authenticate with OpenAI (use your OpenAI api key)
openai.api_key = "your_openai_api_key"

# CLI arguments
parser = argparse.ArgumentParser(description="GitHub README and comment generator using GPT-4")
parser.add_argument("gh_token", help="GitHub personal access token")
parser.add_argument("openai_key", help="OpenAI API key")
parser.add_argument("repo", help="GitHub repository (format: owner/repo)")
parser.add_argument("--revert", action="store_true", help="Revert the last commit made by this script")


args = parser.parse_args()

# Authenticate with GitHub
g = Github(args.gh_token)

# Authenticate with OpenAI
openai.api_key = args.openai_key

# Connect to the GitHub repository
repo = g.get_repo(args.repo)

# Check if revert is specified
if args.revert:
    revert_last_commit(repo)
else:

    # Generate README using GPT-4
    readme_content = generate_readme_gpt4(repo.name)

    # Check if README.md already exists in the repository
    readme_file = None
    try:
        readme_file = repo.get_contents("README.md")
    except github.UnknownObjectException:
        pass

    if readme_file:
        # Update the existing README.md file
        repo.update_file("README.md", "Auto-generated README using GPT-4", readme_content, readme_file.sha)
    else:
        # Create a new README.md file
        repo.create_file("README.md", "Auto-generated README using GPT-4", readme_content)


    # Add comments to code files using GPT-4
    tree = repo.get_git_tree(sha=repo.default_branch, recursive=True)
    for item in tree.tree:
        if item.type == "blob" and item.path.endswith((".py", ".js", ".cpp", ".java", ".tf")):
            file_content = base64.b64decode(repo.get_contents(item.path).content).decode("utf-8")
            updated_file_content = add_comments_gpt4(file_content)

            if updated_file_content != file_content:
                repo.update_file(item.path, "Add comments to code using GPT-4", updated_file_content, repo.get_contents(item.path).sha)

    # Commit and push changes
    # The changes are committed and pushed automatically by the PyGithub library


    # use the following command to run this file
    # python code_doc.py GITHUB_TOKEN OPENAI_API repo_owner/repo_name
