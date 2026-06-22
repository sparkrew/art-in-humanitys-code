import os
import requests
import json
import pycld2 as cld2
import time
import argparse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class GitHubAPIManager:
    def __init__(self, tokens):
        self.tokens = tokens
        self.current_token_index = 0
        self.rate_limits = {}
        
    def get_current_token(self):
        return self.tokens[self.current_token_index]
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.get_current_token()}"}
    
    def rotate_token(self):
        self.current_token_index = (self.current_token_index + 1) % len(self.tokens)
        print(f"Rotated to token {self.current_token_index + 1}/{len(self.tokens)}")
    
    def check_rate_limit(self):
        query = """
        {
          rateLimit {
            limit
            cost
            remaining
            resetAt
          }
        }
        """
        try:
            response = requests.post(
                'https://api.github.com/graphql',
                json={'query': query},
                headers=self.get_headers()
            )
            if response.status_code == 200:
                data = response.json()
                rate_limit = data["data"]["rateLimit"]
                return rate_limit
            return None
        except Exception as e:
            print(f"Error checking rate limit: {e}")
            return None
    
    def wait_for_rate_limit_reset(self, reset_at):
        reset_time = datetime.fromisoformat(reset_at.replace('Z', '+00:00'))
        current_time = datetime.now(reset_time.tzinfo)
        wait_seconds = (reset_time - current_time).total_seconds()
        if wait_seconds > 0:
            print(f"Rate limit exceeded. Waiting {wait_seconds:.0f} seconds until {reset_at}")
            time.sleep(wait_seconds + 5)
    
    def execute_with_retry(self, func, *args, max_retries=3, **kwargs):
        retries = 0
        tokens_tried = 0
        while tokens_tried < len(self.tokens):
            try:
                rate_limit = self.check_rate_limit()
                if rate_limit and rate_limit["remaining"] < 10:
                    print(f"Token {self.current_token_index + 1} has low remaining requests: {rate_limit['remaining']}")
                    if tokens_tried < len(self.tokens) - 1:
                        self.rotate_token()
                        tokens_tried += 1
                        continue
                    else:
                        self.wait_for_rate_limit_reset(rate_limit["resetAt"])
                        tokens_tried = 0
                        continue
                result = func(*args, headers=self.get_headers(), **kwargs)
                return result
                
            except Exception as e:
                error_str = str(e)
                print(f"Error: {error_str}")
                if "rate" in error_str.lower() or retries >= max_retries:
                    if tokens_tried < len(self.tokens) - 1:
                        self.rotate_token()
                        tokens_tried += 1
                        retries = 0
                    else:
                        rate_limit = self.check_rate_limit()
                        if rate_limit:
                            self.wait_for_rate_limit_reset(rate_limit["resetAt"])
                        else:
                            time.sleep(60)
                        tokens_tried = 0
                else:
                    retries += 1
                    time.sleep(2 ** retries)
        raise Exception("Rate limits not reset")


def parse_github_urls(file_path):
    repos = []
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if 'github.com/' in line:
                parts = line.split('github.com/')[-1].split('/')
            else:
                parts = line.split('/')
            
            if len(parts) >= 2:
                owner = parts[0]
                repo = parts[1].split('?')[0].split('#')[0]
                repos.append(f"{owner}/{repo}")
    
    return repos


def run_query_with_headers(query, headers):
    request = requests.post(
        'https://api.github.com/graphql',
        json={'query': query},
        headers=headers
    )
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception(f"Query failed with code {request.status_code}")


def get_user_info(username, headers):
    query = """
    query getUserLocation($login: String!) {
      user(login: $login) {
        login
        location
        createdAt
        bio
      }
    }
    """
    request = requests.post(
        'https://api.github.com/graphql',
        json={"query": query, "variables": {"login": username}},
        headers=headers
    )
    if request.status_code == 200:
        data = request.json()
        return data["data"]["user"]
    else:
        raise Exception(f"Query failed with code {request.status_code}")

def build_single_repo_query(repo):
    owner, name = repo.split('/')
    query = f"""
    {{
      repository(owner: "{owner}", name: "{name}") {{
        nameWithOwner
        createdAt
        primaryLanguage {{
          name
        }}
        languages(first: 10, orderBy: {{field: SIZE, direction: DESC}}) {{
          edges {{
            node {{
              name
            }}
            size
          }}
          totalSize
        }}
        defaultBranchRef {{
          name
          target {{
            ... on Commit {{
              history(first: 100) {{
                totalCount
                edges {{
                  node {{
                    author {{
                      user {{
                        login
                      }}
                    }}
                  }}
                }}
              }}
            }}
          }}
        }}
        object(expression: "HEAD:README.md") {{
          ... on Blob {{
            text
          }}
        }}
      }}
    }}
    """
    return query

def process_repository(repo, api_manager):
    onerepo = {}
    onerepo["name"] = repo["nameWithOwner"]
    onerepo["creation_date"] = repo["createdAt"]
    
    # Extract primary language
    onerepo["primary_language"] = repo["primaryLanguage"]["name"] if repo.get("primaryLanguage") else "none"
    
    # Extract all languages with percentages
    if repo.get("languages") and repo["languages"]["edges"]:
        total_size = repo["languages"]["totalSize"]
        languages_breakdown = []
        for edge in repo["languages"]["edges"]:
            lang_name = edge["node"]["name"]
            lang_size = edge["size"]
            percentage = (lang_size / total_size * 100) if total_size > 0 else 0
            languages_breakdown.append({
                "name": lang_name,
                "percentage": round(percentage, 2)
            })
        onerepo["languages"] = languages_breakdown
    else:
        onerepo["languages"] = []
    
    if not repo.get("defaultBranchRef"):
        print(f"No default branch for {repo['nameWithOwner']}")
        onerepo["nb_commits"] = 0
        onerepo["main_contributor"] = "none"
        onerepo["main_contributor_profile"] = {"location": "none", "bio": "none"}
        onerepo["readme"] = None
        return onerepo
        
    commits = repo["defaultBranchRef"]["target"]["history"]["totalCount"]
    onerepo["nb_commits"] = commits
    contributors = [
        edge["node"]["author"]["user"]["login"]
        for edge in repo["defaultBranchRef"]["target"]["history"]["edges"]
        if edge["node"]["author"]["user"]
    ]
    
    if contributors:
        main_contributor = max(set(contributors), key=contributors.count)
        onerepo["main_contributor"] = main_contributor
        try:
            userprofile = api_manager.execute_with_retry(get_user_info, main_contributor)
            profile = {
                "location": userprofile.get("location") or "none",
                "bio": userprofile.get("bio") or "none"
            }
        except Exception as e:
            print(f"Error fetching profile for {main_contributor}: {e}")
            profile = {"location": "none", "bio": "none"}
    else:
        onerepo["main_contributor"] = "none"
        profile = {"location": "none", "bio": "none"}
    onerepo["main_contributor_profile"] = profile
    readme = repo["object"]["text"] if repo.get("object") else None
    onerepo["readme"] = readme
    
    return onerepo


def main():
    parser = argparse.ArgumentParser(description='Scrape GitHub repositories at scale')
    parser.add_argument('--tokens', required=True, help='Comma-separated GitHub tokens')
    parser.add_argument('--input', required=True, help='Path to file with GitHub URLs (one per line)')
    parser.add_argument('--output', default='repos_data.json', help='Output JSON file')
    parser.add_argument('--batch-size', type=int, default=50, help='Number of repos per batch query')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between batches (seconds)')
    parser.add_argument('--resume', action='store_true', help='Resume from existing output file')
    
    args = parser.parse_args()
    
    tokens = [token.strip() for token in args.tokens.split(',')]
    print(f"Loaded {len(tokens)} token(s)")
    
    api_manager = GitHubAPIManager(tokens)
    
    repos = parse_github_urls(args.input)
    
    all_repos_metadata = []
    processed_repos = set()
    
    if args.resume and os.path.exists(args.output):
        try:
            with open(args.output, 'r') as f:
                all_repos_metadata = json.load(f)
                processed_repos = {repo['name'] for repo in all_repos_metadata}
                print(f"Resuming: {len(all_repos_metadata)} repositories already processed")
        except Exception as e:
            print(f"Error loading existing data: {e}")
            print("Starting fresh...")
    
    repos_to_process = [repo for repo in repos if repo not in processed_repos]
    print(f"Repositories remaining to process: {len(repos_to_process)}")
    
    if not repos_to_process:
        print("All repositories already processed!")
        return
    
    batch_size = args.batch_size
    
    for i in range(0, len(repos_to_process), batch_size):
        batch = repos_to_process[i:i + batch_size]
        print(f"\nProcessing batch {i//batch_size + 1}/{(len(repos_to_process)-1)//batch_size + 1} ({len(batch)} repos)")
        print(f"Total progress: {len(all_repos_metadata)}/{len(repos)} ({100*len(all_repos_metadata)/len(repos):.1f}%)")
        
        for repo_name in batch:
            try:
                query = build_single_repo_query(repo_name)
                result = api_manager.execute_with_retry(run_query_with_headers, query)
                
                if result and "data" in result and "repository" in result["data"]:
                    repo = result["data"]["repository"]
                    
                    if repo:
                        try:
                            repo_data = process_repository(repo, api_manager)
                            all_repos_metadata.append(repo_data)
                            print(f"Processed {repo_data['name']} ({len(all_repos_metadata)}/{len(repos)})")
                        except Exception as e:
                            print(f"Error processing {repo_name}: {e}")
                    else:
                        print(f"Repository not found: {repo_name}")
                else:
                    print(f"Invalid response for {repo_name}")
                
                time.sleep(0.1)
                    
            except Exception as e:
                print(f"Error querying {repo_name}: {e}")
                continue
        
        with open(args.output, 'w') as f:
            json.dump(all_repos_metadata, f, indent=2)
        
        print(f"Progress saved: {len(all_repos_metadata)} repositories")
        
        if i + batch_size < len(repos_to_process):
            time.sleep(args.delay)
    
    print(f"Processed {len(all_repos_metadata)} repositories")
    print(f"Data saved to {args.output}")


if __name__ == "__main__":
    main()
    