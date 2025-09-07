# This is our Reddit Frustration Finder
# It reads Reddit posts and finds people complaining about problems

import praw  # This is a tool that talks to Reddit
import json  # This saves data in a format we can read
from datetime import datetime  # This adds today's date to our files
import os  # This helps us work with files

print("Starting Reddit Frustration Finder...")

# Connect to Reddit using our secret keys
# These keys come from GitHub secrets we set up
reddit = praw.Reddit(
    client_id=os.environ.get('REDDIT_CLIENT_ID'),
    client_secret=os.environ.get('REDDIT_CLIENT_SECRET'),
    user_agent='FrustrationFinder 1.0'  # This is just a name for our program
)

print("Connected to Reddit!")

# List of subreddits we want to check
# These are communities where people often complain about problems
subreddits_to_check = [
    'startups',
    'entrepreneur',
    'webdev',
    'smallbusiness',
    'freelance'
]

# Words that suggest someone is frustrated
# When we see these words, we know someone might be complaining
frustration_words = [
    'hate', 'annoying', 'frustrated', 'sucks', 'impossible',
    'broken', 'doesnt work', "can't", 'wish', 'need',
    'problem', 'issue', 'difficult', 'confused', 'stuck'
]

# This will store all the frustrations we find
all_frustrations = []

# Go through each subreddit
for subreddit_name in subreddits_to_check:
    print(f"Checking r/{subreddit_name}...")
    
    try:
        # Get the subreddit
        subreddit = reddit.subreddit(subreddit_name)
        
        # Look at the 50 newest posts
        for post in subreddit.new(limit=50):
            # Combine the title and text of the post
            full_text = f"{post.title} {post.selftext}".lower()
            
            # Check if any frustration words are in the post
            for word in frustration_words:
                if word in full_text:
                    # We found a frustration! Save it
                    frustration_data = {
                        'subreddit': subreddit_name,
                        'title': post.title,
                        'text': post.selftext[:500],  # First 500 characters
                        'url': f"https://reddit.com{post.permalink}",
                        'score': post.score,  # Number of upvotes
                        'date': datetime.fromtimestamp(post.created_utc).strftime('%Y-%m-%d'),
                        'frustration_word_found': word
                    }
                    all_frustrations.append(frustration_data)
                    print(f"  Found frustration: {post.title[:50]}...")
                    break  # Stop checking words for this post
    
    except Exception as e:
        print(f"  Couldn't check r/{subreddit_name}: {e}")

print(f"\nFound {len(all_frustrations)} total frustrations!")

# Create a folder for today's data
today = datetime.now().strftime('%Y-%m-%d')
os.makedirs(f'data/{today}', exist_ok=True)

# Save the frustrations to a file
output_file = f'data/{today}/reddit_frustrations.json'
with open(output_file, 'w') as f:
    json.dump(all_frustrations, f, indent=2)

print(f"Saved to {output_file}")

# Also create a simple summary for reading
summary_file = f'data/{today}/summary.md'
with open(summary_file, 'w') as f:
    f.write(f"# Frustrations Found on {today}\n\n")
    f.write(f"Total frustrations found: {len(all_frustrations)}\n\n")
    
    # Show top 10 frustrations
    f.write("## Top Frustrations:\n\n")
    for i, frustration in enumerate(all_frustrations[:10], 1):
        f.write(f"{i}. **{frustration['title']}**\n")
        f.write(f"   - Subreddit: r/{frustration['subreddit']}\n")
        f.write(f"   - Score: {frustration['score']}\n")
        f.write(f"   - [Link]({frustration['url']})\n\n")

print(f"Created summary at {summary_file}")
print("Done!")
