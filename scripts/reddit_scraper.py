# Improved Reddit Frustration Finder - Version 2
# This one is much better at finding complaints!

import praw
import json
from datetime import datetime
import os

print("Starting Reddit Frustration Finder v2...")

# Connect to Reddit
reddit = praw.Reddit(
    client_id=os.environ.get('REDDIT_CLIENT_ID'),
    client_secret=os.environ.get('REDDIT_CLIENT_SECRET'),
    user_agent='FrustrationFinder 2.0'
)

print("Connected to Reddit!")

# More subreddits where people complain
subreddits_to_check = [
    'startups',
    'entrepreneur', 
    'webdev',
    'smallbusiness',
    'freelance',
    'Entrepreneur',
    'SaaS',
    'marketing', 
    'ecommerce',
    'productivity'
]

# Much better list of frustration indicators
frustration_words = [
    # Direct complaints
    'hate', 'annoying', 'frustrated', 'sucks', 'terrible', 'awful',
    'broken', 'doesnt work', "doesn't work", "can't", 'cant', 'impossible',
    
    # Problems and issues  
    'problem', 'issue', 'struggle', 'difficult', 'confused', 'stuck',
    'help', 'how do i', 'how to', 'anyone else',
    
    # Wishes and needs
    'wish', 'need', 'want', 'looking for', 'alternative to',
    'tired of', 'sick of', 'fed up',
    
    # Pain points
    'waste', 'slow', 'expensive', 'complicated', 'confusing',
    'why is', 'why does', 'why cant', "why can't"
]

all_frustrations = []

# Search each subreddit more thoroughly
for subreddit_name in subreddits_to_check:
    print(f"\nChecking r/{subreddit_name}...")
    
    try:
        subreddit = reddit.subreddit(subreddit_name)
        
        # Check HOT posts (what's trending now)
        print(f"  Checking hot posts...")
        for post in subreddit.hot(limit=25):
            full_text = f"{post.title} {post.selftext}".lower()
            
            # Count how many frustration words appear
            frustration_score = sum(1 for word in frustration_words if word in full_text)
            
            # If at least 1 frustration word found, save it
            if frustration_score > 0:
                frustration_data = {
                    'subreddit': subreddit_name,
                    'title': post.title,
                    'text': post.selftext[:500] if post.selftext else "No text content",
                    'url': f"https://reddit.com{post.permalink}",
                    'score': post.score,
                    'num_comments': post.num_comments,
                    'date': datetime.fromtimestamp(post.created_utc).strftime('%Y-%m-%d'),
                    'frustration_score': frustration_score
                }
                all_frustrations.append(frustration_data)
                print(f"    ✓ Found: {post.title[:60]}...")
        
        # Check NEW posts (recent complaints)
        print(f"  Checking new posts...")
        for post in subreddit.new(limit=25):
            full_text = f"{post.title} {post.selftext}".lower()
            
            frustration_score = sum(1 for word in frustration_words if word in full_text)
            
            if frustration_score > 0:
                # Don't add duplicates
                if not any(f['url'].endswith(post.permalink) for f in all_frustrations):
                    frustration_data = {
                        'subreddit': subreddit_name,
                        'title': post.title,
                        'text': post.selftext[:500] if post.selftext else "No text content",
                        'url': f"https://reddit.com{post.permalink}",
                        'score': post.score,
                        'num_comments': post.num_comments,
                        'date': datetime.fromtimestamp(post.created_utc).strftime('%Y-%m-%d'),
                        'frustration_score': frustration_score
                    }
                    all_frustrations.append(frustration_data)
                    print(f"    ✓ Found: {post.title[:60]}...")
                    
    except Exception as e:
        print(f"  ✗ Couldn't check r/{subreddit_name}: {e}")

# Sort by frustration score (most frustrated first)
all_frustrations.sort(key=lambda x: x['frustration_score'], reverse=True)

print(f"\n{'='*50}")
print(f"TOTAL FRUSTRATIONS FOUND: {len(all_frustrations)}")
print(f"{'='*50}\n")

# Create data folder
today = datetime.now().strftime('%Y-%m-%d')
os.makedirs(f'data/{today}', exist_ok=True)

# Save the JSON file
output_file = f'data/{today}/reddit_frustrations.json'
with open(output_file, 'w') as f:
    json.dump(all_frustrations, f, indent=2)
print(f"Saved data to {output_file}")

# Create the summary
summary_file = f'data/{today}/summary.md'
with open(summary_file, 'w') as f:
    f.write(f"# Frustrations Found on {today}\n\n")
    f.write(f"**Total frustrations found: {len(all_frustrations)}**\n\n")
    
    if len(all_frustrations) == 0:
        f.write("No frustrations found. Possible issues:\n")
        f.write("- Reddit API might be rate limited\n")
        f.write("- Subreddits might be slow today\n") 
        f.write("- Try running again in a few hours\n")
    else:
        f.write("## Top 15 Frustrations:\n\n")
        for i, frustration in enumerate(all_frustrations[:15], 1):
            f.write(f"### {i}. {frustration['title']}\n")
            f.write(f"- **Subreddit:** r/{frustration['subreddit']}\n")
            f.write(f"- **Score:** {frustration['score']} upvotes\n")
            f.write(f"- **Comments:** {frustration['num_comments']}\n")
            f.write(f"- **Frustration Level:** {frustration['frustration_score']}/10\n")
            if frustration['text'] and frustration['text'] != "No text content":
                preview = frustration['text'][:150] + "..." if len(frustration['text']) > 150 else frustration['text']
                f.write(f"- **Preview:** {preview}\n")
            f.write(f"- **[View on Reddit]({frustration['url']})**\n\n")

print(f"Created summary at {summary_file}")
print("\nDone! Check the summary.md file for results.")
