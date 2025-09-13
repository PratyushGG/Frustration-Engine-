# Real SaaS Opportunity Finder v9 - FIXED VERSION
# Only finds ACTUAL problems people would pay to solve

import praw
import json
import csv
from datetime import datetime
import os
import time
import re
from collections import defaultdict, Counter
import pytz

EDT = pytz.timezone('US/Eastern')
today = datetime.now(EDT).strftime('%Y-%m-%d')
current_time = datetime.now(EDT).strftime('%Y-%m-%d %H:%M:%S EDT')

print("=" * 60)
print(f"REAL SAAS OPPORTUNITY FINDER V9")
print(f"Finding ONLY actual software requests")
print(f"Started: {current_time}")
print("=" * 60)

reddit = praw.Reddit(
    client_id=os.environ.get('REDDIT_CLIENT_ID'),
    client_secret=os.environ.get('REDDIT_CLIENT_SECRET'),
    user_agent='RealSaaSFinder 9.0'
)

# STRICT FILTERS - Must explicitly ask for software/tool
MUST_HAVE_PHRASES = [
    # Direct software requests
    "looking for a tool",
    "looking for software",
    "looking for an app",
    "looking for a solution",
    "looking for a service",
    "looking for a platform",
    "need a tool",
    "need software",
    "need an app",
    "searching for a tool",
    "searching for software",
    
    # Questions about tools
    "is there a tool",
    "is there software",
    "is there an app",
    "does anyone know a tool",
    "does anyone use a tool",
    "can anyone recommend",
    "what tool do you use",
    "what software do you use",
    "what app do you use",
    
    # Replacement requests
    "alternative to",
    "replacement for",
    "substitute for",
    "better than",
    "cheaper than",
    "instead of",
    
    # Problem statements
    "how do you automate",
    "how do you manage",
    "how do you track",
    "how do you handle",
    "how to automate",
    "way to automate",
    
    # Pain points
    "doing this manually",
    "do it manually",
    "spreadsheet is getting",
    "excel is getting",
    "takes me hours",
    "takes hours to",
    "waste hours",
    "time consuming",
    "tedious process"
]

# EXCLUDE these - they're NOT software requests
EXCLUDE_PHRASES = [
    # General questions/discussions
    "just a reminder",
    "what's the point",
    "is there really",
    "why is there",
    "why are",
    "can i refuse",
    "should i",
    "am i the",
    "unpopular opinion",
    "hot take",
    "rant",
    "venting",
    "psa",
    "eli5",
    
    # Stories/situations
    "got scammed",
    "what happened",
    "update:",
    "update -",
    "success story",
    "failed",
    "passed",
    "i built",
    "we built",
    "just launched",
    "introducing",
    
    # Not software related
    "looking for a job",
    "looking for work", 
    "looking for employees",
    "looking for a contractor",
    "looking for advice",
    "looking for tips",
    "looking for feedback",
    "looking for opinions"
]

def is_real_saas_opportunity(post):
    """Strict validation - must be explicitly asking for software"""
    
    title = post.title.lower()
    body = (post.selftext[:1000] if post.selftext else '').lower()
    full_text = f"{title} {body}"
    
    # Must have minimum engagement
    if post.score < 3 or post.num_comments < 2:
        return False
    
    # Must have at least one software request phrase
    has_request = any(phrase in full_text for phrase in MUST_HAVE_PHRASES)
    if not has_request:
        return False
    
    # Must NOT be a general discussion/rant
    is_excluded = any(phrase in full_text for phrase in EXCLUDE_PHRASES)
    if is_excluded:
        return False
    
    # Title should be a question or request
    if not any(indicator in title for indicator in ['?', 'looking for', 'need', 'alternative', 'how do', 'how to', 'is there', 'recommend']):
        return False
    
    return True

def extract_problem_details(post):
    """Extract the actual problem they're trying to solve"""
    
    text = f"{post.title}\n{post.selftext[:1000] if post.selftext else ''}"
    
    details = {
        'problem_type': '',
        'current_tools': [],
        'pain_points': [],
        'use_case': '',
        'budget_signals': [],
        'urgency': 'normal'
    }
    
    # Identify problem type
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['automate', 'automation', 'manual', 'repetitive']):
        details['problem_type'] = 'automation'
    elif any(word in text_lower for word in ['integrate', 'connect', 'sync', 'api']):
        details['problem_type'] = 'integration'
    elif any(word in text_lower for word in ['track', 'manage', 'organize', 'monitor']):
        details['problem_type'] = 'management'
    elif any(word in text_lower for word in ['analyze', 'report', 'dashboard', 'metrics']):
        details['problem_type'] = 'analytics'
    elif any(word in text_lower for word in ['communicate', 'collaborate', 'share']):
        details['problem_type'] = 'collaboration'
    else:
        details['problem_type'] = 'general'
    
    # Find current tools mentioned
    common_tools = [
        'excel', 'sheets', 'notion', 'airtable', 'slack', 'asana', 'trello',
        'monday', 'clickup', 'zapier', 'salesforce', 'hubspot', 'quickbooks',
        'xero', 'stripe', 'shopify', 'wordpress', 'mailchimp', 'zendesk'
    ]
    details['current_tools'] = [tool for tool in common_tools if tool in text_lower]
    
    # Extract pain points
    if 'manual' in text_lower:
        details['pain_points'].append('manual_process')
    if any(word in text_lower for word in ['hours', 'time consuming', 'tedious']):
        details['pain_points'].append('time_consuming')
    if any(word in text_lower for word in ['expensive', 'costly', 'pricing']):
        details['pain_points'].append('cost')
    if any(word in text_lower for word in ['complex', 'complicated', 'difficult']):
        details['pain_points'].append('complexity')
    if any(word in text_lower for word in ["doesn't", "can't", "won't", "missing"]):
        details['pain_points'].append('missing_feature')
    
    # Extract use case (first 100 chars of actual request)
    use_case_match = re.search(r'(?:looking for|need|want).{0,100}', text_lower)
    if use_case_match:
        details['use_case'] = use_case_match.group()[:100]
    
    # Budget signals
    money_mentions = re.findall(r'\$[\d,]+', text)
    if money_mentions:
        details['budget_signals'] = money_mentions[:3]
    
    # Urgency
    if any(word in text_lower for word in ['urgent', 'asap', 'immediately', 'desperate']):
        details['urgency'] = 'high'
    elif any(word in text_lower for word in ['soon', 'quickly', 'this week']):
        details['urgency'] = 'medium'
    
    return details

def calculate_opportunity_value(post, details):
    """Score based on commercial viability"""
    
    score = 0
    
    # Problem type scoring
    problem_values = {
        'automation': 20,
        'integration': 20,
        'management': 15,
        'analytics': 15,
        'collaboration': 10,
        'general': 5
    }
    score += problem_values.get(details['problem_type'], 5)
    
    # Pain point scoring
    score += len(details['pain_points']) * 10
    
    # Current tools mentioned (means they're already paying)
    score += len(details['current_tools']) * 5
    
    # Budget signals
    if details['budget_signals']:
        score += 15
    
    # Urgency
    if details['urgency'] == 'high':
        score += 10
    elif details['urgency'] == 'medium':
        score += 5
    
    # Engagement
    score += min(post.score, 50) // 5
    score += min(post.num_comments, 30) // 3
    
    return score

# TARGET SUBREDDITS - where people actually ask for tools
BUSINESS_SUBREDDITS = [
    # High-value businesses
    'Entrepreneur', 'startups', 'smallbusiness', 'SaaS',
    'ecommerce', 'shopify', 'FulfillmentByAmazon',
    
    # Professional services
    'freelance', 'webdev', 'marketing', 'realtors',
    'accounting', 'Bookkeeping', 'MSP', 'agency',
    
    # Specific industries
    'restaurateur', 'PropertyManagement', 'logistics',
    'Construction', 'nonprofit', 'consulting',
    
    # Tool-specific (people looking for alternatives)
    'notion', 'excel', 'salesforce', 'monday'
]

# Main execution
real_opportunities = []
opportunities_by_type = defaultdict(list)

print("\nSearching for REAL SaaS opportunities...")
print("-" * 60)

for subreddit_name in BUSINESS_SUBREDDITS[:10]:  # Process 10 subreddits
    try:
        print(f"\n📊 Scanning r/{subreddit_name}...")
        subreddit = reddit.subreddit(subreddit_name)
        found_in_sub = 0
        
        # Search queries that find real requests
        search_queries = [
            '"looking for" tool OR software OR app',
            '"is there a" tool OR software',
            '"alternative to"',
            '"how do you" manage OR track OR automate',
            '"what tool" OR "what software"',
            'recommend tool OR software',
            '"tired of" OR "frustrated with"'
        ]
        
        for query in search_queries[:3]:  # Use top 3 queries
            try:
                results = subreddit.search(query, time_filter='month', limit=20)
                
                for post in results:
                    # STRICT VALIDATION
                    if not is_real_saas_opportunity(post):
                        continue
                    
                    # Extract details
                    details = extract_problem_details(post)
                    
                    # Calculate value
                    value_score = calculate_opportunity_value(post, details)
                    
                    # Only keep valuable opportunities
                    if value_score < 20:
                        continue
                    
                    # Check for validation in comments
                    validation_count = 0
                    try:
                        post.comments.replace_more(limit=0)
                        for comment in post.comments.list()[:30]:
                            comment_text = comment.body.lower()
                            if any(phrase in comment_text for phrase in 
                                  ['same', 'me too', 'also looking', 'need this', 'following']):
                                validation_count += 1
                    except:
                        pass
                    
                    opportunity = {
                        'title': post.title,
                        'subreddit': subreddit_name,
                        'url': f"https://reddit.com{post.permalink}",
                        'score': post.score,
                        'comments': post.num_comments,
                        'value_score': value_score,
                        'validation_count': validation_count,
                        'problem_type': details['problem_type'],
                        'current_tools': details['current_tools'],
                        'pain_points': details['pain_points'],
                        'use_case': details['use_case'],
                        'budget_signals': details['budget_signals'],
                        'urgency': details['urgency'],
                        'date': datetime.fromtimestamp(post.created_utc, EDT).strftime('%Y-%m-%d'),
                        'preview': post.selftext[:300] if post.selftext else ''
                    }
                    
                    real_opportunities.append(opportunity)
                    opportunities_by_type[details['problem_type']].append(opportunity)
                    found_in_sub += 1
                    
                    print(f"  ✓ Found: {post.title[:60]}... (score: {value_score})")
                
                time.sleep(2)  # Rate limiting
                
            except Exception as e:
                print(f"  ⚠ Search error: {e}")
                continue
        
        print(f"  Total found in r/{subreddit_name}: {found_in_sub}")
        time.sleep(3)  # Rate limiting between subreddits
        
    except Exception as e:
        print(f"  ✗ Error with r/{subreddit_name}: {e}")

# Sort by value
real_opportunities.sort(key=lambda x: x['value_score'], reverse=True)

print("\n" + "=" * 60)
print(f"FOUND {len(real_opportunities)} REAL SAAS OPPORTUNITIES")
print("=" * 60)

# Save outputs
os.makedirs(f'data/{today}', exist_ok=True)

# 1. Raw JSON
with open(f'data/{today}/reddit_frustrations.json', 'w') as f:
    json.dump(real_opportunities, f, indent=2)

# 2. Formatted report
with open(f'data/{today}/summary.md', 'w') as f:
    f.write(f"# 🎯 Real SaaS Opportunities from Reddit - {today}\n\n")
    f.write(f"*Found {len(real_opportunities)} actual software requests*\n\n")
    
    if len(real_opportunities) == 0:
        f.write("## No opportunities found\n\n")
        f.write("This could mean:\n")
        f.write("- Reddit API rate limits\n")
        f.write("- Need to search different subreddits\n")
        f.write("- Try running at a different time\n")
    else:
        # Validated opportunities (multiple people need it)
        validated = [o for o in real_opportunities if o['validation_count'] >= 2]
        
        if validated:
            f.write("## 🔥 VALIDATED OPPORTUNITIES (Multiple People Need This)\n\n")
            for i, opp in enumerate(validated[:10], 1):
                f.write(f"### {i}. {opp['title']}\n\n")
                f.write(f"**Problem Type:** {opp['problem_type'].title()}\n\n")
                
                if opp['use_case']:
                    f.write(f"**What they need:** {opp['use_case']}\n\n")
                
                if opp['current_tools']:
                    f.write(f"**Currently using:** {', '.join(opp['current_tools'])}\n\n")
                
                if opp['pain_points']:
                    f.write(f"**Pain points:** {', '.join(opp['pain_points'])}\n\n")
                
                if opp['budget_signals']:
                    f.write(f"**Budget mentioned:** {', '.join(opp['budget_signals'])}\n\n")
                
                f.write(f"**Validation:** {opp['validation_count']} others need this\n")
                f.write(f"**Urgency:** {opp['urgency']}\n")
                f.write(f"**Opportunity Score:** {opp['value_score']}\n\n")
                f.write(f"[View Discussion]({opp['url']})\n\n")
                f.write("-" * 40 + "\n\n")
        
        # Group by problem type
        f.write("## 💡 OPPORTUNITIES BY TYPE\n\n")
        
        for prob_type, opps in opportunities_by_type.items():
            if opps:
                f.write(f"### {prob_type.title()} Opportunities ({len(opps)})\n\n")
                for opp in opps[:5]:
                    f.write(f"- **{opp['title'][:80]}**\n")
                    if opp['use_case']:
                        f.write(f"  - Need: {opp['use_case'][:60]}...\n")
                    f.write(f"  - Score: {opp['value_score']} | r/{opp['subreddit']}\n")
                    f.write(f"  - [Link]({opp['url']})\n\n")
        
        # All opportunities
        f.write("## 📋 ALL OPPORTUNITIES RANKED\n\n")
        
        for i, opp in enumerate(real_opportunities[:50], 1):
            f.write(f"{i}. **{opp['title']}**\n")
            f.write(f"   - Type: {opp['problem_type']} | ")
            f.write(f"Score: {opp['value_score']} | ")
            f.write(f"r/{opp['subreddit']} | ")
            if opp['validation_count'] > 0:
                f.write(f"Validated: {opp['validation_count']} | ")
            f.write(f"[Link]({opp['url']})\n")

# 3. CSV for analysis
csv_file = f'data/{today}/opportunities.csv'
with open(csv_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow([
        'Title', 'Problem Type', 'Value Score', 'Validation Count',
        'Current Tools', 'Pain Points', 'Use Case', 'Budget Signals',
        'Urgency', 'Subreddit', 'URL'
    ])
    
    for opp in real_opportunities:
        writer.writerow([
            opp['title'][:100],
            opp['problem_type'],
            opp['value_score'],
            opp['validation_count'],
            ', '.join(opp['current_tools']),
            ', '.join(opp['pain_points']),
            opp['use_case'],
            ', '.join(opp['budget_signals']),
            opp['urgency'],
            opp['subreddit'],
            opp['url']
        ])

print(f"\n✅ Analysis complete!")
print(f"Real opportunities: {len(real_opportunities)}")
print(f"Check data/{today}/summary.md for results")
