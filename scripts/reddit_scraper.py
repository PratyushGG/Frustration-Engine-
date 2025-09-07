# Advanced Reddit Frustration Finder v3
# Focuses on COMMERCIAL problems worth solving

import praw
import json
import csv
from datetime import datetime, timedelta
import os
import time
from collections import defaultdict, Counter
import re

print("Starting Commercial Opportunity Finder v3...")

reddit = praw.Reddit(
    client_id=os.environ.get('REDDIT_CLIENT_ID'),
    client_secret=os.environ.get('REDDIT_CLIENT_SECRET'),
    user_agent='OpportunityFinder 3.0'
)

# TARGET: Business-focused subreddits
business_subreddits = [
    'Entrepreneur', 'startups', 'SaaS', 'smallbusiness',
    'ecommerce', 'shopify', 'marketing', 'digital_marketing',
    'freelance', 'juststart', 'EntrepreneurRideAlong',
    'indiehackers', 'microsaas', 'buildinpublic'
]

# PROFESSIONAL subreddits (people who pay for solutions)
professional_subreddits = [
    'webdev', 'web_design', 'dataengineering', 'datascience',
    'ProductManagement', 'projectmanagement', 'sales',
    'realestate', 'accounting', 'bookkeeping', 'excel'
]

# SPECIFIC tool complaint subreddits
tool_subreddits = [
    'wordpress', 'shopify', 'notion', 'googlesheets',
    'monday', 'asana', 'slack', 'MSAccess', 'PowerBI'
]

# COMMERCIAL PROBLEM PATTERNS
commercial_patterns = {
    'integration_problems': [
        r'integrate.*with', r'connect.*to', r'sync.*between',
        r'import.*from', r'export.*to', r'api.*broken',
        r'webhook.*not working', r'zapier.*expensive'
    ],
    'automation_needs': [
        r'manually.*every', r'waste.*hours', r'repetitive.*task',
        r'automate.*process', r'spend.*time.*doing',
        r'copy.*paste', r'have to.*every day'
    ],
    'scaling_issues': [
        r'too many.*clients', r'can\'t.*scale', r'growing.*fast',
        r'manage.*multiple', r'keep track.*of', r'overwhelmed.*with'
    ],
    'cost_problems': [
        r'\$.*per month', r'too expensive', r'pricing.*crazy',
        r'cheaper.*alternative', r'budget.*friendly',
        r'can\'t afford', r'enterprise.*pricing'
    ],
    'missing_features': [
        r'wish.*could', r'need.*feature', r'doesn\'t.*support',
        r'can\'t.*find.*tool', r'looking for.*solution',
        r'alternative.*to', r'but.*without'
    ],
    'workflow_problems': [
        r'switch.*between', r'multiple.*tools', r'different.*platforms',
        r'no.*central', r'scattered.*across', r'have to.*login'
    ]
}

# BUSINESS VALUE INDICATORS
business_indicators = [
    'clients', 'customers', 'revenue', 'business', 'company',
    'team', 'employees', 'workflow', 'process', 'efficiency',
    'productivity', 'ROI', 'cost', 'budget', 'scale', 'growth'
]

def calculate_commercial_score(text):
    """Score how likely this is a solvable business problem"""
    score = 0
    text_lower = text.lower()
    
    # Check for commercial patterns
    for category, patterns in commercial_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                score += 3
    
    # Check for business indicators
    for indicator in business_indicators:
        if indicator in text_lower:
            score += 2
    
    # Bonus for specific pain points
    if '$' in text or 'hour' in text_lower or 'time' in text_lower:
        score += 2
    
    # Penalty for personal problems
    personal_words = ['my life', 'my wife', 'my kids', 'depressed', 'lonely', 'my relationship']
    for word in personal_words:
        if word in text_lower:
            score -= 5
    
    return score

def extract_problem_category(text):
    """Categorize the type of problem"""
    text_lower = text.lower()
    
    for category, patterns in commercial_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return category
    
    return 'general_frustration'

all_frustrations = []
problem_clusters = defaultdict(list)

# Aggressive scraping within limits
for subreddit_list in [business_subreddits, professional_subreddits, tool_subreddits]:
    for subreddit_name in subreddit_list:
        print(f"\nMining r/{subreddit_name} for commercial opportunities...")
        
        try:
            subreddit = reddit.subreddit(subreddit_name)
            
            # Multiple search queries for finding problems
            problem_searches = [
                'title:"how to" OR title:"how do"',
                'title:"looking for" OR title:"need help"',
                'title:"alternative to" OR title:"replacement for"',
                'title:"tired of" OR title:"sick of"',
                'title:"why can\'t" OR title:"why doesn\'t"',
                'title:"is there" OR title:"anyone know"',
                'title:"struggling with" OR title:"frustrated with"',
                'title:"waste" OR title:"manual" OR title:"tedious"',
                'selftext:"every day" OR selftext:"every week"',
                'selftext:"hours" AND (selftext:"waste" OR selftext:"spend")'
            ]
            
            # Search with multiple queries
            for query in problem_searches[:3]:  # Limit to avoid rate limits
                try:
                    for post in subreddit.search(query, time_filter='month', limit=10):
                        full_text = f"{post.title} {post.selftext}"
                        
                        commercial_score = calculate_commercial_score(full_text)
                        
                        if commercial_score >= 5:  # Only keep commercial problems
                            category = extract_problem_category(full_text)
                            
                            frustration_data = {
                                'subreddit': subreddit_name,
                                'title': post.title,
                                'text': post.selftext[:1000] if post.selftext else "",
                                'url': f"https://reddit.com{post.permalink}",
                                'score': post.score,
                                'num_comments': post.num_comments,
                                'date': datetime.fromtimestamp(post.created_utc).strftime('%Y-%m-%d'),
                                'commercial_score': commercial_score,
                                'category': category,
                                'author': str(post.author),
                                'upvote_ratio': post.upvote_ratio
                            }
                            
                            all_frustrations.append(frustration_data)
                            problem_clusters[category].append(frustration_data)
                            print(f"  💰 Commercial opportunity: {post.title[:60]}...")
                
                    time.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    print(f"  Search failed: {e}")
                    continue
            
            # Also check hot posts for high-engagement problems
            for post in subreddit.hot(limit=25):
                if post.score > 10 and post.num_comments > 5:
                    full_text = f"{post.title} {post.selftext}"
                    commercial_score = calculate_commercial_score(full_text)
                    
                    if commercial_score >= 5:
                        category = extract_problem_category(full_text)
                        
                        # Avoid duplicates
                        if not any(f['url'].endswith(post.permalink) for f in all_frustrations):
                            frustration_data = {
                                'subreddit': subreddit_name,
                                'title': post.title,
                                'text': post.selftext[:1000] if post.selftext else "",
                                'url': f"https://reddit.com{post.permalink}",
                                'score': post.score,
                                'num_comments': post.num_comments,
                                'date': datetime.fromtimestamp(post.created_utc).strftime('%Y-%m-%d'),
                                'commercial_score': commercial_score,
                                'category': category,
                                'author': str(post.author),
                                'upvote_ratio': post.upvote_ratio
                            }
                            
                            all_frustrations.append(frustration_data)
                            problem_clusters[category].append(frustration_data)
                            
            time.sleep(2)  # Rate limiting between subreddits
            
        except Exception as e:
            print(f"  ✗ Couldn't check r/{subreddit_name}: {e}")

# Sort by commercial value
all_frustrations.sort(key=lambda x: x['commercial_score'], reverse=True)

print(f"\n{'='*60}")
print(f"COMMERCIAL OPPORTUNITIES FOUND: {len(all_frustrations)}")
print(f"{'='*60}\n")

# Create output directory
today = datetime.now().strftime('%Y-%m-%d')
os.makedirs(f'data/{today}', exist_ok=True)

# Save detailed JSON
with open(f'data/{today}/commercial_frustrations.json', 'w') as f:
    json.dump(all_frustrations, f, indent=2)

# Create CSV with problem clusters
csv_file = f'data/{today}/problem_clusters.csv'
with open(csv_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Category', 'Problem Count', 'Avg Score', 'Top Problem', 'Example URL'])
    
    for category, problems in problem_clusters.items():
        if problems:
            avg_score = sum(p['commercial_score'] for p in problems) / len(problems)
            top_problem = max(problems, key=lambda x: x['score'])
            writer.writerow([
                category.replace('_', ' ').title(),
                len(problems),
                f"{avg_score:.1f}",
                top_problem['title'][:100],
                top_problem['url']
            ])

# Create actionable summary
summary_file = f'data/{today}/opportunities.md'
with open(summary_file, 'w') as f:
    f.write(f"# Commercial Opportunities Report - {today}\n\n")
    f.write(f"**Total Commercial Problems Found: {len(all_frustrations)}**\n\n")
    
    # Problem category breakdown
    f.write("## Problem Categories\n\n")
    f.write("| Category | Count | Business Potential |\n")
    f.write("|----------|-------|-------------------|\n")
    
    for category, problems in sorted(problem_clusters.items(), key=lambda x: len(x[1]), reverse=True):
        if problems:
            potential = "🔥 High" if len(problems) > 10 else "✅ Medium" if len(problems) > 5 else "💡 Low"
            f.write(f"| {category.replace('_', ' ').title()} | {len(problems)} | {potential} |\n")
    
    f.write("\n## Top 10 Commercial Opportunities\n\n")
    
    for i, frustration in enumerate(all_frustrations[:10], 1):
        f.write(f"### {i}. {frustration['title']}\n")
        f.write(f"- **Category:** {frustration['category'].replace('_', ' ').title()}\n")
        f.write(f"- **Commercial Score:** {frustration['commercial_score']}/20\n")
        f.write(f"- **Engagement:** {frustration['score']} upvotes, {frustration['num_comments']} comments\n")
        f.write(f"- **Subreddit:** r/{frustration['subreddit']}\n")
        
        # Extract key pain points
        if frustration['text']:
            sentences = frustration['text'].split('.')[:2]
            if sentences:
                f.write(f"- **Pain Point:** {'. '.join(sentences)}...\n")
        
        f.write(f"- **[Validate on Reddit]({frustration['url']})**\n\n")
    
    # Emerging patterns
    f.write("\n## Emerging Patterns\n\n")
    
    # Find repeated themes
    all_titles = ' '.join([f['title'].lower() for f in all_frustrations])
    common_tools = ['notion', 'excel', 'google sheets', 'slack', 'zapier', 'airtable', 'monday']
    
    f.write("**Most Mentioned Tools with Problems:**\n")
    for tool in common_tools:
        count = all_titles.count(tool)
        if count > 0:
            f.write(f"- {tool.title()}: {count} mentions\n")
    
    f.write("\n**Hottest Problem Categories:**\n")
    for category, problems in sorted(problem_clusters.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
        if problems:
            f.write(f"- {category.replace('_', ' ').title()}: {len(problems)} problems\n")

print(f"Created opportunity report at {summary_file}")
print(f"Created problem clusters CSV at {csv_file}")
print("\n✅ Done! Check opportunities.md for actionable insights.")
