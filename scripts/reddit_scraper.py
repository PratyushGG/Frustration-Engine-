# SaaS Opportunity Finder v8 - Based on proven problem-finding methodology
# Finds specific, actionable problems like the Medium article

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
print(f"SAAS OPPORTUNITY FINDER V8")
print(f"Finding specific problems people would pay to solve")
print(f"Started: {current_time}")
print("=" * 60)

reddit = praw.Reddit(
    client_id=os.environ.get('REDDIT_CLIENT_ID'),
    client_secret=os.environ.get('REDDIT_CLIENT_SECRET'),
    user_agent='SaaSOpportunityFinder 8.0'
)

# EXACT PHRASES that indicate someone would PAY for a solution
# These are based on the Medium article patterns
BUYING_INTENT_PHRASES = [
    # Direct tool requests (highest intent)
    "is there a tool",
    "looking for a tool",
    "looking for software",
    "anyone know of a tool",
    "does anyone use",
    "what tool do you use",
    "recommend a tool",
    "suggest a tool",
    "is there an app",
    "looking for an app",
    
    # Current solution problems (replacement opportunity)
    "alternative to",
    "replacement for",
    "better than",
    "cheaper than",
    "instead of",
    "switching from",
    "tired of using",
    "hate using",
    "frustrated with",
    
    # Manual process complaints (automation opportunity)
    "doing this manually",
    "manual process",
    "by hand",
    "copy and paste",
    "spreadsheet for",
    "excel for",
    "takes me hours",
    "spend hours",
    "waste time",
    "tedious process",
    
    # Integration problems (connection opportunity)
    "doesn't integrate",
    "won't sync",
    "can't connect",
    "no integration",
    "doesn't work with",
    "incompatible with",
    "can't export",
    "can't import",
    
    # Missing features (gap opportunity)
    "wish it could",
    "wish there was",
    "if only it",
    "doesn't have",
    "missing feature",
    "can't even",
    "no way to",
    "impossible to",
    
    # Price complaints (cheaper alternative opportunity)
    "too expensive",
    "can't afford",
    "overpriced",
    "costs too much",
    "pricing is crazy",
    "per user pricing",
    "enterprise pricing"
]

# SPECIFIC PROBLEM CATEGORIES from the article
PROBLEM_CATEGORIES = {
    'workflow_automation': {
        'keywords': ['automate', 'workflow', 'manual', 'repetitive', 'process', 'streamline'],
        'value_proposition': 'Save X hours per week',
        'price_range': '$50-500/mo'
    },
    'data_integration': {
        'keywords': ['integrate', 'sync', 'connect', 'api', 'import', 'export', 'transfer'],
        'value_proposition': 'Connect X with Y seamlessly',
        'price_range': '$100-1000/mo'
    },
    'industry_specific_crm': {
        'keywords': ['crm', 'clients', 'customers', 'contacts', 'pipeline', 'leads'],
        'value_proposition': 'CRM built specifically for [industry]',
        'price_range': '$50-300/user/mo'
    },
    'compliance_documentation': {
        'keywords': ['compliance', 'audit', 'documentation', 'regulation', 'certification'],
        'value_proposition': 'Stay compliant without the headache',
        'price_range': '$200-2000/mo'
    },
    'team_coordination': {
        'keywords': ['team', 'collaboration', 'coordinate', 'communication', 'remote'],
        'value_proposition': 'Keep your team in sync',
        'price_range': '$10-50/user/mo'
    },
    'customer_communication': {
        'keywords': ['customer', 'client', 'communication', 'support', 'feedback'],
        'value_proposition': 'Never miss a customer message',
        'price_range': '$50-500/mo'
    },
    'reporting_analytics': {
        'keywords': ['report', 'analytics', 'dashboard', 'metrics', 'kpi', 'tracking'],
        'value_proposition': 'All your metrics in one place',
        'price_range': '$100-1000/mo'
    },
    'scheduling_booking': {
        'keywords': ['scheduling', 'booking', 'appointment', 'calendar', 'availability'],
        'value_proposition': 'Eliminate back-and-forth scheduling',
        'price_range': '$20-200/mo'
    },
    'inventory_management': {
        'keywords': ['inventory', 'stock', 'warehouse', 'supply', 'ordering'],
        'value_proposition': 'Never run out of stock again',
        'price_range': '$100-1000/mo'
    },
    'content_generation': {
        'keywords': ['content', 'generate', 'create', 'write', 'design', 'template'],
        'value_proposition': 'Create X in minutes, not hours',
        'price_range': '$30-300/mo'
    }
}

# HIGH-VALUE SUBREDDITS organized by business potential
TARGET_SUBREDDITS = {
    'high_ticket_businesses': [
        # These businesses have high customer lifetime values
        'realtors', 'RealEstate', 'PropertyManagement',
        'LawFirm', 'Lawyertalk', 'insurance',
        'consulting', 'MSP', 'agency'
    ],
    'volume_businesses': [
        # These need efficiency at scale
        'ecommerce', 'FulfillmentByAmazon', 'shopify',
        'restaurateur', 'smallbusiness', 'Entrepreneur'
    ],
    'professional_services': [
        # These bill by the hour and hate inefficiency
        'accounting', 'Bookkeeping', 'tax',
        'webdev', 'freelance', 'graphic_design',
        'marketing', 'SEO', 'content_marketing'
    ],
    'specific_tools': [
        # People already paying for tools (easier to switch)
        'salesforce', 'excel', 'googlesheets',
        'notion', 'wordpress', 'shopify',
        'QuickBooks', 'photoshop'
    ],
    'operations_heavy': [
        # These have complex operations
        'logistics', 'supplychain', 'Construction',
        'manufacturing', 'ProjectManagement',
        'operations', 'facilitiesmanagement'
    ]
}

def extract_saas_opportunity(post, comments=[]):
    """Extract specific SaaS opportunity details"""
    text = f"{post.title}\n{post.selftext}".lower()
    
    opportunity = {
        'problem_statement': '',
        'current_solution': '',
        'desired_features': [],
        'willingness_to_pay': '',
        'urgency_level': '',
        'market_size_indicator': '',
        'competition': [],
        'mvp_complexity': '',
        'category': '',
        'specific_use_case': ''
    }
    
    # Extract problem statement (usually in the title or first sentence)
    if '?' in post.title:
        opportunity['problem_statement'] = post.title
    else:
        # Get first sentence of body
        sentences = post.selftext.split('.')
        if sentences:
            opportunity['problem_statement'] = sentences[0][:200]
    
    # Find current solution
    current_patterns = [
        r'currently (?:using|use|have) ([\w\s]+)',
        r'been using ([\w\s]+)',
        r'tried ([\w\s]+)',
        r'stuck with ([\w\s]+)',
        r'we use ([\w\s]+) but'
    ]
    for pattern in current_patterns:
        match = re.search(pattern, text)
        if match:
            opportunity['current_solution'] = match.group(1).strip()
            break
    
    # Extract desired features (what they want)
    want_patterns = [
        r'want(?:s|ed)? (?:to|a|an) ([\w\s,]+)',
        r'need(?:s|ed)? (?:to|a|an) ([\w\s,]+)',
        r'looking for (?:something that|a way to) ([\w\s,]+)',
        r'wish(?:es|ed)? (?:it|there was|for) ([\w\s,]+)'
    ]
    for pattern in want_patterns:
        matches = re.findall(pattern, text)
        opportunity['desired_features'].extend([m.strip()[:100] for m in matches])
    
    # Willingness to pay indicators
    price_mentions = re.findall(r'\$[\d,]+(?:\.\d{2})?(?:/mo|/month|/year)?', text)
    if price_mentions:
        opportunity['willingness_to_pay'] = ', '.join(price_mentions[:3])
    elif 'budget' in text:
        opportunity['willingness_to_pay'] = 'budget-conscious'
    elif 'enterprise' in text or 'company' in text:
        opportunity['willingness_to_pay'] = 'enterprise-budget'
    elif 'free' in text:
        opportunity['willingness_to_pay'] = 'looking-for-free'
    else:
        opportunity['willingness_to_pay'] = 'unknown'
    
    # Urgency level
    if any(word in text for word in ['urgent', 'asap', 'immediately', 'desperate']):
        opportunity['urgency_level'] = 'high'
    elif any(word in text for word in ['soon', 'quickly', 'this month']):
        opportunity['urgency_level'] = 'medium'
    else:
        opportunity['urgency_level'] = 'low'
    
    # Market size indicator (how many people have this problem)
    if comments:
        agreements = sum(1 for c in comments 
                        if any(phrase in c.body.lower() 
                              for phrase in ['same', 'me too', 'also looking', 'following', 'need this']))
        if agreements > 10:
            opportunity['market_size_indicator'] = 'large'
        elif agreements > 5:
            opportunity['market_size_indicator'] = 'medium'
        else:
            opportunity['market_size_indicator'] = 'small'
    
    # Competition mentioned
    tools_mentioned = re.findall(r'\b(?:use|using|tried)\s+(\w+(?:\s+\w+)?)\b', text)
    opportunity['competition'] = list(set(tools_mentioned))[:5]
    
    # MVP complexity estimate
    if 'simple' in text or 'basic' in text:
        opportunity['mvp_complexity'] = 'simple'
    elif 'integrate' in text or 'api' in text:
        opportunity['mvp_complexity'] = 'medium'
    elif 'enterprise' in text or 'complex' in text:
        opportunity['mvp_complexity'] = 'complex'
    else:
        opportunity['mvp_complexity'] = 'unknown'
    
    # Categorize the opportunity
    for category, info in PROBLEM_CATEGORIES.items():
        if any(kw in text for kw in info['keywords']):
            opportunity['category'] = category
            break
    
    # Extract specific use case
    use_case_patterns = [
        r'for (?:my|our) ([\w\s]+)',
        r'to (?:manage|track|handle) ([\w\s]+)',
        r'helps? (?:me|us) ([\w\s]+)'
    ]
    for pattern in use_case_patterns:
        match = re.search(pattern, text)
        if match:
            opportunity['specific_use_case'] = match.group(1).strip()[:100]
            break
    
    return opportunity

def calculate_opportunity_score(post, opportunity, comments=[]):
    """Score the opportunity based on multiple factors"""
    score = 0
    text = f"{post.title} {post.selftext}".lower()
    
    # Buying intent (most important)
    for phrase in BUYING_INTENT_PHRASES:
        if phrase in text:
            score += 10
            break
    
    # Money mentioned (strong signal)
    if opportunity['willingness_to_pay'] and opportunity['willingness_to_pay'] != 'unknown':
        if '$' in opportunity['willingness_to_pay']:
            score += 15
        elif opportunity['willingness_to_pay'] == 'enterprise-budget':
            score += 20
    
    # Problem validation (others have same problem)
    if opportunity['market_size_indicator'] == 'large':
        score += 15
    elif opportunity['market_size_indicator'] == 'medium':
        score += 10
    
    # Current solution exists but inadequate (replacement opportunity)
    if opportunity['current_solution']:
        score += 10
    
    # Clear desired features (they know what they want)
    score += len(opportunity['desired_features']) * 5
    
    # Urgency
    if opportunity['urgency_level'] == 'high':
        score += 10
    elif opportunity['urgency_level'] == 'medium':
        score += 5
    
    # Engagement metrics
    score += post.score // 5
    score += post.num_comments // 3
    
    # Category bonus (some categories are more valuable)
    valuable_categories = ['compliance_documentation', 'data_integration', 'industry_specific_crm']
    if opportunity['category'] in valuable_categories:
        score += 10
    
    return score

# Main execution
saas_opportunities = []
category_opportunities = defaultdict(list)
validated_opportunities = []  # Opportunities with multiple people confirming need

print("\nSearching for specific SaaS opportunities...")
print("-" * 60)

for category_name, subreddits in TARGET_SUBREDDITS.items():
    print(f"\n💼 Category: {category_name.upper()}")
    
    for subreddit_name in subreddits[:3]:  # Limit to prevent rate limiting
        try:
            print(f"  → Scanning r/{subreddit_name}...")
            subreddit = reddit.subreddit(subreddit_name)
            
            # Search for high-intent queries
            high_intent_searches = [
                '"looking for" tool OR software OR app',
                '"is there" tool OR software OR app',
                '"alternative to"',
                '"recommend" software OR tool OR app',
                '"frustrated with" OR "tired of"',
                '"takes hours" OR "waste time"',
                '"manually" OR "by hand"',
                '"doesn\'t integrate" OR "can\'t export"'
            ]
            
            for search_query in high_intent_searches[:3]:
                try:
                    for post in subreddit.search(search_query, time_filter='year', limit=15):
                        # Must have engagement
                        if post.score < 5 or post.num_comments < 3:
                            continue
                        
                        # Load comments for validation
                        post.comments.replace_more(limit=0)
                        comments = post.comments.list()[:50]
                        
                        # Extract opportunity
                        opportunity = extract_saas_opportunity(post, comments)
                        score = calculate_opportunity_score(post, opportunity, comments)
                        
                        if score < 20:  # Only keep high-potential opportunities
                            continue
                        
                        # Check if others validated this need
                        validation_comments = [
                            c for c in comments 
                            if any(phrase in c.body.lower() 
                                  for phrase in ['same', 'me too', 'also looking', 'need this'])
                        ]
                        
                        saas_opp = {
                            'title': post.title,
                            'subreddit': subreddit_name,
                            'category': category_name,
                            'url': f"https://reddit.com{post.permalink}",
                            'score': post.score,
                            'comments': post.num_comments,
                            'opportunity_score': score,
                            'opportunity': opportunity,
                            'validation_count': len(validation_comments),
                            'date': datetime.fromtimestamp(post.created_utc, EDT).strftime('%Y-%m-%d'),
                            'preview': post.selftext[:500] if post.selftext else ''
                        }
                        
                        saas_opportunities.append(saas_opp)
                        
                        if opportunity['category']:
                            category_opportunities[opportunity['category']].append(saas_opp)
                        
                        if len(validation_comments) >= 3:
                            validated_opportunities.append(saas_opp)
                        
                        print(f"    💡 SaaS Opportunity: {post.title[:50]}... (score: {score})")
                    
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"    ⚠ Search error: {e}")
                    continue
            
            # Also check hot posts
            for post in subreddit.hot(limit=10):
                if post.score > 20 and post.num_comments > 10:
                    title_lower = post.title.lower()
                    
                    # Quick check for opportunity indicators
                    if any(phrase in title_lower for phrase in ['tool', 'software', 'app', 'solution', 'alternative']):
                        post.comments.replace_more(limit=0)
                        comments = post.comments.list()[:50]
                        
                        opportunity = extract_saas_opportunity(post, comments)
                        score = calculate_opportunity_score(post, opportunity, comments)
                        
                        if score >= 20:
                            saas_opp = {
                                'title': post.title,
                                'subreddit': subreddit_name,
                                'category': category_name,
                                'url': f"https://reddit.com{post.permalink}",
                                'score': post.score,
                                'comments': post.num_comments,
                                'opportunity_score': score,
                                'opportunity': opportunity,
                                'validation_count': 0,
                                'date': datetime.fromtimestamp(post.created_utc, EDT).strftime('%Y-%m-%d'),
                                'preview': post.selftext[:500] if post.selftext else ''
                            }
                            
                            # Avoid duplicates
                            if not any(o['url'] == saas_opp['url'] for o in saas_opportunities):
                                saas_opportunities.append(saas_opp)
                                print(f"    💡 Found in hot: {post.title[:50]}...")
            
            time.sleep(3)
            
        except Exception as e:
            print(f"  ✗ Error with r/{subreddit_name}: {e}")

# Sort by opportunity score
saas_opportunities.sort(key=lambda x: x['opportunity_score'], reverse=True)
validated_opportunities.sort(key=lambda x: x['opportunity_score'], reverse=True)

print("\n" + "=" * 60)
print("ANALYSIS COMPLETE")
print("=" * 60)
print(f"SaaS opportunities found: {len(saas_opportunities)}")
print(f"Validated opportunities: {len(validated_opportunities)}")
print(f"Categories covered: {len(category_opportunities)}")

# Save outputs
os.makedirs(f'data/{today}', exist_ok=True)

# 1. Raw JSON
with open(f'data/{today}/reddit_frustrations.json', 'w') as f:
    json.dump(saas_opportunities, f, indent=2)

# 2. Main SaaS opportunities report
with open(f'data/{today}/summary.md', 'w') as f:
    f.write(f"# 🚀 50 SaaS Ideas from Reddit - {today}\n\n")
    f.write(f"*Found {len(saas_opportunities)} specific SaaS opportunities from Reddit*\n\n")
    
    # Top validated opportunities
    if validated_opportunities:
        f.write("## 🔥 TOP 10 VALIDATED SAAS OPPORTUNITIES\n")
        f.write("*Multiple people confirmed they need these solutions*\n\n")
        
        for i, opp in enumerate(validated_opportunities[:10], 1):
            o = opp['opportunity']
            f.write(f"### {i}. {opp['title']}\n\n")
            
            # The pitch
            problem = o['problem_statement'] or opp['title']
            f.write(f"**The Problem:** {problem}\n\n")
            
            if o['current_solution']:
                f.write(f"**Current Solution:** {o['current_solution']} (not good enough)\n\n")
            
            if o['desired_features']:
                f.write(f"**What They Want:**\n")
                for feature in o['desired_features'][:3]:
                    f.write(f"- {feature}\n")
                f.write("\n")
            
            if o['willingness_to_pay'] and '$' in o['willingness_to_pay']:
                f.write(f"**Price Point:** {o['willingness_to_pay']}\n\n")
            
            f.write(f"**Validation:** {opp['validation_count']} people said they need this\n\n")
            
            # The opportunity
            if o['category'] in PROBLEM_CATEGORIES:
                cat_info = PROBLEM_CATEGORIES[o['category']]
                f.write(f"**SaaS Category:** {o['category'].replace('_', ' ').title()}\n")
                f.write(f"**Value Prop:** {cat_info['value_proposition']}\n")
                f.write(f"**Pricing Range:** {cat_info['price_range']}\n\n")
            
            f.write(f"**Complexity:** {o['mvp_complexity']}\n")
            f.write(f"**Market Size:** {o['market_size_indicator']}\n\n")
            
            f.write(f"[See Original Discussion]({opp['url']})\n\n")
            f.write("-" * 40 + "\n\n")
    
    # Ideas by category
    f.write("## 💡 IDEAS BY CATEGORY\n\n")
    
    for category, opps in category_opportunities.items():
        if opps:
            cat_info = PROBLEM_CATEGORIES.get(category, {})
            f.write(f"### {category.replace('_', ' ').title()}\n")
            f.write(f"*{cat_info.get('value_proposition', '')}*\n\n")
            
            for opp in opps[:5]:
                f.write(f"- **{opp['title'][:80]}...**\n")
                f.write(f"  - Score: {opp['opportunity_score']}\n")
                f.write(f"  - r/{opp['subreddit']}\n")
                f.write(f"  - [Link]({opp['url']})\n\n")
    
    # Quick wins (simple MVPs)
    simple_mvps = [o for o in saas_opportunities if o['opportunity']['mvp_complexity'] == 'simple']
    if simple_mvps:
        f.write("## ⚡ QUICK WINS (Simple MVPs)\n\n")
        for opp in simple_mvps[:5]:
            f.write(f"- **{opp['title']}**\n")
            f.write(f"  - Build: {opp['opportunity']['specific_use_case'] or 'Simple tool'}\n")
            f.write(f"  - [Link]({opp['url']})\n\n")
    
    # High-value opportunities (enterprise/high budget)
    high_value = [o for o in saas_opportunities 
                  if o['opportunity']['willingness_to_pay'] == 'enterprise-budget']
    if high_value:
        f.write("## 💰 HIGH-VALUE OPPORTUNITIES\n\n")
        for opp in high_value[:5]:
            f.write(f"- **{opp['title']}**\n")
            f.write(f"  - Target: Enterprise/Business\n")
            f.write(f"  - [Link]({opp['url']})\n\n")
    
    # All opportunities list
    f.write("## 📋 ALL 50 SAAS OPPORTUNITIES\n\n")
    
    for i, opp in enumerate(saas_opportunities[:50], 1):
        o = opp['opportunity']
        f.write(f"{i}. **{opp['title']}**\n")
        f.write(f"   - Score: {opp['opportunity_score']} | ")
        f.write(f"r/{opp['subreddit']} | ")
        if o['category']:
            f.write(f"{o['category'].replace('_', ' ').title()} | ")
        if o['willingness_to_pay'] and o['willingness_to_pay'] != 'unknown':
            f.write(f"Budget: {o['willingness_to_pay']} | ")
        f.write(f"[Link]({opp['url']})\n")

# 3. CSV for analysis
csv_file = f'data/{today}/saas_opportunities.csv'
with open(csv_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow([
        'Title', 'Category', 'Opportunity Score', 'Problem Statement',
        'Current Solution', 'Desired Features', 'Willingness to Pay',
        'Market Size', 'MVP Complexity', 'Validation Count', 'URL'
    ])
    
    for opp in saas_opportunities:
        o = opp['opportunity']
        writer.writerow([
            opp['title'][:100],
            o['category'],
            opp['opportunity_score'],
            o['problem_statement'][:200],
            o['current_solution'],
            ', '.join(o['desired_features'][:3]),
            o['willingness_to_pay'],
            o['market_size_indicator'],
            o['mvp_complexity'],
            opp['validation_count'],
            opp['url']
        ])

print(f"\n✅ Found {len(saas_opportunities)} SaaS opportunities!")
print(f"Check data/{today}/summary.md for your 50 SaaS ideas")
