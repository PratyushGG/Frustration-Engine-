# Advanced Commercial Problem Finder v4
# This actually finds REAL problems people will pay to solve

import praw
import json
import csv
from datetime import datetime, timedelta
import os
import time
from collections import defaultdict, Counter
import re

print("Starting Advanced Commercial Problem Finder v4...")
print("=" * 60)

reddit = praw.Reddit(
    client_id=os.environ.get('REDDIT_CLIENT_ID'),
    client_secret=os.environ.get('REDDIT_CLIENT_SECRET'),
    user_agent='ProblemFinder 4.0'
)

# KILLER SEARCH QUERIES - These find actual problems
problem_finding_queries = [
    # People actively looking for solutions
    '"looking for" tool OR software OR app OR solution',
    '"need" alternative to',
    '"tired of" OR "sick of" OR "frustrated with"',
    '"waste" hours OR time OR day',
    '"there has to be" better',
    '"why isn\'t there" OR "why is there no"',
    '"anyone know" tool OR software OR solution',
    '"recommend" tool OR software -"I recommend"',  # Exclude recommendations, find requests
    
    # Money/Time bleeding problems
    '"spending" hours OR "takes me" hours',
    '"paying too much" OR "too expensive"',
    '"lost" client OR customer OR sale because',
    '"manually" OR "by hand" OR "copy paste"',
    '"excel" OR "spreadsheet" track OR manage',
    
    # Integration/Workflow problems  
    '"doesn\'t integrate" OR "won\'t sync"',
    '"switch between" OR "multiple tools"',
    '"export" then "import"',
    
    # Validation signals
    '"clients keep asking" OR "customers want"',
    '"built my own" OR "made a script"',
    '"hired" VA OR assistant OR freelancer "just to"'
]

# MONEY SUBREDDITS - People who actually pay for solutions
high_value_subreddits = {
    'business_owners': [
        'smallbusiness', 'ecommerce', 'shopify', 'FulfillmentByAmazon',
        'restaurateur', 'realtors', 'insurance', 'accounting'
    ],
    'tech_professionals': [
        'webdev', 'devops', 'sysadmin', 'dataengineering', 'analytics',
        'ProductManagement', 'projectmanagement', 'agile'
    ],
    'agencies_freelancers': [
        'freelance', 'marketing', 'PPC', 'SEO', 'content_marketing',
        'socialmediamarketing', 'web_design', 'graphic_design'
    ],
    'saas_startup': [
        'SaaS', 'startups', 'Entrepreneur', 'indiehackers',
        'EntrepreneurRideAlong', 'buildinpublic', 'microsaas'
    ],
    'specific_tools': [
        'Notion', 'salesforce', 'wordpress', 'Shopify', 'excel',
        'googlesheets', 'zapier', 'PowerBI', 'tableau'
    ]
}

def calculate_problem_value_score(post, comments=[]):
    """Score how valuable/solvable this problem is"""
    score = 0
    full_text = f"{post.title} {post.selftext}".lower()
    
    # STRONG BUYING SIGNALS
    buying_signals = {
        'paying': 5, 'cost': 4, 'expensive': 5, 'budget': 4,
        'hours': 4, 'waste': 4, 'manually': 4, 'time': 3,
        'client': 5, 'customer': 5, 'business': 4, 'revenue': 5,
        'scale': 4, 'grow': 3, 'team': 3, 'workflow': 4
    }
    
    for signal, weight in buying_signals.items():
        if signal in full_text:
            score += weight
    
    # VALIDATION MULTIPLIERS
    if post.score > 50:
        score *= 1.5
    if post.num_comments > 20:
        score *= 1.3
    if '$' in full_text:
        score *= 1.5
    
    # Check if others have same problem (validation)
    if comments:
        agreement_phrases = ['same', 'me too', 'this', 'exactly', 'also looking']
        agreements = sum(1 for c in comments if any(phrase in c.body.lower() for phrase in agreement_phrases))
        if agreements > 3:
            score *= 2
    
    # PENALTY for non-commercial
    penalty_words = ['hobby', 'personal', 'free', 'student', 'learning']
    for word in penalty_words:
        if word in full_text:
            score *= 0.5
    
    return int(score)

def extract_specific_problem(post, comments=[]):
    """Extract the actual specific problem"""
    problem = {
        'title': post.title,
        'core_issue': '',
        'current_solution': '',
        'desired_outcome': '',
        'urgency': 'low',
        'budget_indicator': 'unknown'
    }
    
    text = f"{post.title} {post.selftext}".lower()
    
    # Find current solution they're unhappy with
    current_patterns = [
        r'currently using (.*?) but',
        r'we use (.*?) but',
        r'tried (.*?) but',
        r'using (.*?) and it'
    ]
    for pattern in current_patterns:
        match = re.search(pattern, text)
        if match:
            problem['current_solution'] = match.group(1)
            break
    
    # Find desired outcome
    desire_patterns = [
        r'looking for (.*?)[\.\,]',
        r'need something that (.*?)[\.\,]',
        r'want to (.*?)[\.\,]',
        r'trying to (.*?)[\.\,]'
    ]
    for pattern in desire_patterns:
        match = re.search(pattern, text)
        if match:
            problem['desired_outcome'] = match.group(1)[:100]
            break
    
    # Urgency indicators
    if any(word in text for word in ['urgent', 'asap', 'immediately', 'desperate']):
        problem['urgency'] = 'high'
    elif any(word in text for word in ['soon', 'quickly', 'this month']):
        problem['urgency'] = 'medium'
    
    # Budget indicators
    if '$' in post.title or '$' in post.selftext:
        # Try to extract dollar amount
        dollar_match = re.search(r'\$(\d+)', text)
        if dollar_match:
            problem['budget_indicator'] = f"${dollar_match.group(1)}"
    elif 'enterprise' in text:
        problem['budget_indicator'] = 'enterprise'
    elif 'budget' in text or 'cheap' in text or 'affordable' in text:
        problem['budget_indicator'] = 'budget-conscious'
    
    # Extract core issue from title or first sentence
    if '?' in post.title:
        problem['core_issue'] = post.title.split('?')[0] + '?'
    else:
        problem['core_issue'] = post.title[:100]
    
    return problem

# Storage for our findings
all_problems = []
problem_patterns = defaultdict(int)
tool_complaints = defaultdict(list)
validated_problems = []  # Problems with multiple people having same issue

print(f"Scanning {sum(len(subs) for subs in high_value_subreddits.values())} high-value subreddits...")
print("=" * 60)

# SYSTEMATIC SEARCH
for category, subreddits in high_value_subreddits.items():
    print(f"\n📊 Analyzing {category.upper()} subreddits...")
    
    for subreddit_name in subreddits[:5]:  # Limit for testing
        try:
            print(f"  Scanning r/{subreddit_name}...")
            subreddit = reddit.subreddit(subreddit_name)
            
            # Method 1: Targeted searches
            for query in problem_finding_queries[:3]:  # Use top 3 queries per subreddit
                try:
                    results = subreddit.search(query, time_filter='month', limit=10)
                    
                    for post in results:
                        # Quick validation - is this a real problem?
                        if post.score < 3 or post.num_comments < 2:
                            continue
                        
                        # Load some comments for validation
                        post.comments.replace_more(limit=0)
                        comments = post.comments.list()[:20]
                        
                        # Calculate value
                        value_score = calculate_problem_value_score(post, comments)
                        
                        if value_score > 10:  # Threshold for "worth solving"
                            problem_details = extract_specific_problem(post, comments)
                            
                            problem_data = {
                                'category': category,
                                'subreddit': subreddit_name,
                                'title': post.title,
                                'details': problem_details,
                                'url': f"https://reddit.com{post.permalink}",
                                'score': post.score,
                                'comments': post.num_comments,
                                'value_score': value_score,
                                'date': datetime.fromtimestamp(post.created_utc).strftime('%Y-%m-%d'),
                                'author': str(post.author),
                                'text_preview': post.selftext[:500] if post.selftext else ''
                            }
                            
                            all_problems.append(problem_data)
                            
                            # Track patterns
                            for word in problem_details['core_issue'].lower().split():
                                if len(word) > 4:  # Skip small words
                                    problem_patterns[word] += 1
                            
                            # Track tool complaints
                            if problem_details['current_solution']:
                                tool_complaints[problem_details['current_solution']].append(problem_data)
                            
                            # Check if others validated this problem
                            validation_count = sum(1 for c in comments 
                                                 if any(phrase in c.body.lower() 
                                                       for phrase in ['same', 'me too', 'exactly']))
                            if validation_count > 2:
                                validated_problems.append(problem_data)
                            
                            print(f"    💰 Found: {post.title[:60]}... (value: {value_score})")
                    
                    time.sleep(2)  # Respect rate limits
                    
                except Exception as e:
                    print(f"    Search error: {e}")
                    continue
            
            # Method 2: Check hot posts for problems in comments
            print(f"    Scanning hot posts for hidden problems...")
            for post in subreddit.hot(limit=10):
                if post.score > 50 and post.num_comments > 20:
                    # This might be a discussion with problems in comments
                    post.comments.replace_more(limit=0)
                    comments = post.comments.list()[:50]
                    
                    for comment in comments:
                        if comment.score > 5:
                            comment_text = comment.body.lower()
                            
                            # Check if comment contains a problem
                            problem_keywords = ['hate', 'annoying', 'frustrat', 'waste', 'manual', 
                                              'expensive', 'doesn\'t', 'can\'t', 'wish', 'need']
                            
                            if any(keyword in comment_text for keyword in problem_keywords):
                                # Found a problem in comments!
                                if len(comment.body) > 50 and len(comment.body) < 1000:
                                    problem_data = {
                                        'category': category,
                                        'subreddit': subreddit_name,
                                        'title': f"Comment problem: {comment.body[:100]}...",
                                        'details': {
                                            'core_issue': comment.body[:200],
                                            'from_comment': True
                                        },
                                        'url': f"https://reddit.com{comment.permalink}",
                                        'score': comment.score,
                                        'value_score': 10,  # Base score for comment problems
                                        'date': datetime.fromtimestamp(comment.created_utc).strftime('%Y-%m-%d'),
                                        'source_post': post.title
                                    }
                                    
                                    all_problems.append(problem_data)
            
            time.sleep(3)  # Rate limit between subreddits
            
        except Exception as e:
            print(f"  ✗ Error with r/{subreddit_name}: {e}")

# ANALYSIS AND OUTPUT
print(f"\n{'='*60}")
print(f"ANALYSIS COMPLETE")
print(f"{'='*60}")
print(f"Total problems found: {len(all_problems)}")
print(f"Validated problems: {len(validated_problems)}")
print(f"Unique tool complaints: {len(tool_complaints)}")

# Sort by value
all_problems.sort(key=lambda x: x['value_score'], reverse=True)
validated_problems.sort(key=lambda x: x['value_score'], reverse=True)

# Save the data
today = datetime.now().strftime('%Y-%m-%d')
os.makedirs(f'data/{today}', exist_ok=True)

# 1. Save raw JSON
with open(f'data/{today}/real_problems.json', 'w') as f:
    json.dump(all_problems, f, indent=2)

# 2. Create actionable report
report_file = f'data/{today}/actionable_opportunities.md'
with open(report_file, 'w') as f:
    f.write(f"# 🎯 Real Commercial Opportunities - {today}\n\n")
    f.write(f"*Found {len(all_problems)} real problems from {sum(len(subs) for subs in high_value_subreddits.values())} subreddits*\n\n")
    
    # Validated problems (multiple people have it)
    f.write("## 🔥 VALIDATED PROBLEMS (Multiple People Confirmed)\n\n")
    if validated_problems:
        for i, prob in enumerate(validated_problems[:5], 1):
            f.write(f"### {i}. {prob['title']}\n")
            f.write(f"- **Value Score:** {prob['value_score']}\n")
            f.write(f"- **Current Solution:** {prob['details'].get('current_solution', 'None mentioned')}\n")
            f.write(f"- **Desired Outcome:** {prob['details'].get('desired_outcome', 'Not specified')}\n")
            f.write(f"- **Budget Signal:** {prob['details'].get('budget_indicator', 'Unknown')}\n")
            f.write(f"- **Urgency:** {prob['details'].get('urgency', 'Low')}\n")
            f.write(f"- **[Validate Further]({prob['url']})**\n\n")
    else:
        f.write("*No strongly validated problems found - need more data*\n\n")
    
    # Tool replacement opportunities
    f.write("## 🛠️ Tool Replacement Opportunities\n\n")
    if tool_complaints:
        f.write("| Current Tool | # Complaints | Opportunity |\n")
        f.write("|-------------|--------------|-------------|\n")
        for tool, complaints in sorted(tool_complaints.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
            if tool and len(complaints) > 0:
                f.write(f"| {tool} | {len(complaints)} | Build better {tool} |\n")
    
    # Problem patterns
    f.write("\n## 📊 Most Common Problem Words\n\n")
    common_problems = sorted(problem_patterns.items(), key=lambda x: x[1], reverse=True)[:20]
    f.write("| Word | Frequency | Indicates |\n")
    f.write("|------|-----------|----------|\n")
    for word, count in common_problems:
        if count > 2:
            problem_type = "Unknown"
            if word in ['integrate', 'sync', 'connect', 'api']:
                problem_type = "Integration need"
            elif word in ['manual', 'automate', 'time', 'hours']:
                problem_type = "Automation opportunity"
            elif word in ['expensive', 'cost', 'price', 'budget']:
                problem_type = "Pricing opportunity"
            f.write(f"| {word} | {count} | {problem_type} |\n")
    
    # Top opportunities by category
    f.write("\n## 💡 Top Problems by Industry\n\n")
    for category in high_value_subreddits.keys():
        category_problems = [p for p in all_problems if p['category'] == category]
        if category_problems:
            f.write(f"**{category.replace('_', ' ').title()}**\n")
            for prob in category_problems[:3]:
                f.write(f"- {prob['title'][:80]}... (score: {prob['value_score']})\n")
            f.write("\n")
    
    # Specific actionable ideas
    f.write("## 🚀 Specific Product Ideas Based on Data\n\n")
    
    # Generate ideas based on patterns
    ideas = []
    
    if 'integrate' in problem_patterns and problem_patterns['integrate'] > 3:
        ideas.append({
            'name': 'Universal Integration Platform',
            'problem': f"Found {problem_patterns['integrate']} integration problems",
            'solution': 'Zapier-like tool for specific niche or cheaper alternative',
            'validation': f"{problem_patterns['integrate']} people mentioned integration issues"
        })
    
    if 'manual' in problem_patterns and problem_patterns['manual'] > 3:
        ideas.append({
            'name': 'Process Automation Tool',
            'problem': f"Found {problem_patterns['manual']} manual process complaints",
            'solution': 'No-code automation for specific repetitive task',
            'validation': f"{problem_patterns['manual']} people doing things manually"
        })
    
    if len(tool_complaints) > 0:
        top_tool = sorted(tool_complaints.items(), key=lambda x: len(x[1]), reverse=True)[0]
        ideas.append({
            'name': f'Better {top_tool[0].title()}',
            'problem': f"{len(top_tool[1])} complaints about {top_tool[0]}",
            'solution': f'Clone {top_tool[0]} but fix the main complaints',
            'validation': f"{len(top_tool[1])} unhappy users ready to switch"
        })
    
    for i, idea in enumerate(ideas[:5], 1):
        f.write(f"{i}. **{idea['name']}**\n")
        f.write(f"   - Problem: {idea['problem']}\n")
        f.write(f"   - Solution: {idea['solution']}\n")
        f.write(f"   - Validation: {idea['validation']}\n\n")
    
    # Next steps
    f.write("## ✅ Next Steps\n\n")
    f.write("1. **Pick ONE problem** from the validated list\n")
    f.write("2. **DM the people** who posted these problems\n")
    f.write("3. **Create a landing page** describing your solution\n")
    f.write("4. **Post in same subreddit** asking if others have this problem\n")
    f.write("5. **Build MVP** only after getting 10+ interested people\n\n")

# 3. Create CSV for spreadsheet analysis
csv_file = f'data/{today}/problems_database.csv'
with open(csv_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Title', 'Category', 'Subreddit', 'Value Score', 'Current Solution', 
                     'Desired Outcome', 'Budget Signal', 'Urgency', 'URL'])
    
    for prob in all_problems[:100]:  # Top 100
        writer.writerow([
            prob['title'][:100],
            prob['category'],
            prob['subreddit'],
            prob['value_score'],
            prob['details'].get('current_solution', ''),
            prob['details'].get('desired_outcome', ''),
            prob['details'].get('budget_indicator', ''),
            prob['details'].get('urgency', ''),
            prob['url']
        ])

print(f"\n✅ Reports created:")
print(f"  - {report_file}")
print(f"  - {csv_file}")
print(f"  - data/{today}/real_problems.json")
