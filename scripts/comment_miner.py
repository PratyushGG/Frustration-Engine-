# Comment Deep Diver - Finds hidden problems in discussions
# This mines the comments where people REALLY complain

import praw
import json
import os
from datetime import datetime
from collections import defaultdict

print("Starting Comment Mining Operation...")

reddit = praw.Reddit(
    client_id=os.environ.get('REDDIT_CLIENT_ID'),
    client_secret=os.environ.get('REDDIT_CLIENT_SECRET'),
    user_agent='CommentMiner 1.0'
)

# Posts that trigger the best problem discussions
discussion_triggers = [
    'what tool', 'what software', 'what app',
    'what do you use', 'how do you manage', 'how do you handle',
    'what\'s your stack', 'what\'s your setup', 'what\'s your workflow',
    'recommend', 'looking for', 'alternatives'
]

# Target subreddits with good discussions
discussion_subreddits = [
    'Entrepreneur', 'startups', 'smallbusiness',
    'webdev', 'marketing', 'ecommerce'
]

hidden_problems = []

for subreddit_name in discussion_subreddits:
    print(f"\nMining r/{subreddit_name} comments...")
    
    try:
        subreddit = reddit.subreddit(subreddit_name)
        
        # Find discussion posts
        for post in subreddit.hot(limit=25):
            title_lower = post.title.lower()
            
            # Is this a discussion post?
            if any(trigger in title_lower for trigger in discussion_triggers):
                if post.num_comments > 10:
                    print(f"  Found discussion: {post.title[:50]}...")
                    
                    # Load ALL comments
                    post.comments.replace_more(limit=None)
                    all_comments = post.comments.list()
                    
                    for comment in all_comments:
                        if comment.score > 3:  # Validated by upvotes
                            comment_lower = comment.body.lower()
                            
                            # Problem indicators in comments
                            if any(indicator in comment_lower for indicator in [
                                'hate', 'annoying', 'frustrat', 'sucks',
                                'doesn\'t', 'can\'t', 'wish', 'expensive',
                                'manual', 'hours', 'waste'
                            ]):
                                # Extract the tool being complained about
                                tool_mentioned = 'Unknown'
                                common_tools = ['notion', 'excel', 'slack', 'zapier', 
                                              'airtable', 'monday', 'asana', 'trello']
                                for tool in common_tools:
                                    if tool in comment_lower:
                                        tool_mentioned = tool
                                        break
                                
                                problem = {
                                    'source_post': post.title,
                                    'post_url': f"https://reddit.com{post.permalink}",
                                    'comment': comment.body[:500],
                                    'comment_url': f"https://reddit.com{comment.permalink}",
                                    'score': comment.score,
                                    'tool_mentioned': tool_mentioned,
                                    'subreddit': subreddit_name
                                }
                                
                                hidden_problems.append(problem)
                                
                                # Check replies for validation
                                for reply in comment.replies:
                                    if any(word in reply.body.lower() for word in ['same', 'exactly', 'this', 'agree']):
                                        problem['validated'] = True
                                        break
    
    except Exception as e:
        print(f"  Error: {e}")

# Save hidden problems
today = datetime.now().strftime('%Y-%m-%d')
os.makedirs(f'data/{today}', exist_ok=True)

with open(f'data/{today}/comment_problems.json', 'w') as f:
    json.dump(hidden_problems, f, indent=2)

# Create comment insights report
with open(f'data/{today}/comment_insights.md', 'w') as f:
    f.write(f"# Hidden Problems from Comments\n\n")
    f.write(f"Found {len(hidden_problems)} problems in comments\n\n")
    
    # Group by tool
    tool_problems = defaultdict(list)
    for prob in hidden_problems:
        tool_problems[prob['tool_mentioned']].append(prob)
    
    for tool, problems in sorted(tool_problems.items(), key=lambda x: len(x[1]), reverse=True):
        if len(problems) > 1:
            f.write(f"\n## {tool.title()} Problems ({len(problems)} complaints)\n")
            for prob in problems[:3]:
                f.write(f"- \"{prob['comment'][:150]}...\"\n")
                f.write(f"  [View comment]({prob['comment_url']})\n\n")

print(f"Found {len(hidden_problems)} hidden problems in comments!")
