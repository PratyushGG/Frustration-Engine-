# AI Opportunity Analyzer
# Analyzes frustrations to find business opportunities

import json
import os
from datetime import datetime
from collections import Counter, defaultdict
import re

print("Starting AI Opportunity Analyzer...")

def find_solution_opportunities(frustrations):
    """Identify specific product opportunities"""
    
    opportunities = []
    
    # Pattern matching for specific opportunities
    opportunity_patterns = {
        'Integration Platform': {
            'keywords': ['integrate', 'connect', 'sync', 'api', 'webhook', 'zapier'],
            'min_mentions': 5,
            'potential_solution': 'Build a Zapier alternative for specific niche',
            'market_size': 'High',
            'difficulty': 'Medium'
        },
        'Automation Tool': {
            'keywords': ['automate', 'manual', 'repetitive', 'every day', 'waste time', 'hours'],
            'min_mentions': 8,
            'potential_solution': 'No-code automation for repetitive tasks',
            'market_size': 'High',
            'difficulty': 'Low-Medium'
        },
        'Cheaper Alternative': {
            'keywords': ['expensive', 'pricing', 'afford', 'budget', 'alternative', 'cheaper'],
            'min_mentions': 10,
            'potential_solution': 'Budget-friendly clone of expensive tool',
            'market_size': 'Medium-High',
            'difficulty': 'Low'
        },
        'Workflow Manager': {
            'keywords': ['multiple tools', 'switch between', 'scattered', 'centralize', 'dashboard'],
            'min_mentions': 5,
            'potential_solution': 'Unified dashboard/workflow tool',
            'market_size': 'Medium',
            'difficulty': 'Medium'
        },
        'Data Migration': {
            'keywords': ['export', 'import', 'migrate', 'transfer', 'move from', 'switch from'],
            'min_mentions': 4,
            'potential_solution': 'One-click migration service',
            'market_size': 'Medium',
            'difficulty': 'Low'
        },
        'Analytics Dashboard': {
            'keywords': ['track', 'metrics', 'analytics', 'reporting', 'insights', 'data'],
            'min_mentions': 6,
            'potential_solution': 'Simple analytics for specific use case',
            'market_size': 'High',
            'difficulty': 'Medium'
        },
        'Chrome Extension': {
            'keywords': ['browser', 'chrome', 'extension', 'plugin', 'bookmark', 'tab'],
            'min_mentions': 3,
            'potential_solution': 'Browser extension to solve specific workflow',
            'market_size': 'Low-Medium',
            'difficulty': 'Low'
        },
        'Mobile App Gap': {
            'keywords': ['mobile', 'ios', 'android', 'app', 'phone', 'on the go'],
            'min_mentions': 4,
            'potential_solution': 'Mobile app for desktop-only tool',
            'market_size': 'Medium',
            'difficulty': 'Medium-High'
        }
    }
    
    for opp_name, pattern in opportunity_patterns.items():
        count = 0
        examples = []
        
        for frustration in frustrations:
            text = f"{frustration['title']} {frustration.get('text', '')}".lower()
            if any(keyword in text for keyword in pattern['keywords']):
                count += 1
                examples.append({
                    'title': frustration['title'],
                    'url': frustration['url'],
                    'score': frustration.get('score', 0)
                })
        
        if count >= pattern['min_mentions']:
            opportunities.append({
                'type': opp_name,
                'frequency': count,
                'solution': pattern['potential_solution'],
                'market_size': pattern['market_size'],
                'difficulty': pattern['difficulty'],
                'examples': sorted(examples, key=lambda x: x['score'], reverse=True)[:3]
            })
    
    return sorted(opportunities, key=lambda x: x['frequency'], reverse=True)

def analyze_tool_problems(frustrations):
    """Find which existing tools have the most complaints"""
    
    tool_mentions = defaultdict(list)
    
    # Common tools people complain about
    tools_to_track = [
        'notion', 'excel', 'google sheets', 'slack', 'zapier', 'airtable', 
        'monday', 'asana', 'trello', 'jira', 'salesforce', 'hubspot',
        'mailchimp', 'wordpress', 'shopify', 'stripe', 'quickbooks',
        'zoom', 'calendly', 'typeform', 'canva', 'figma', 'photoshop'
    ]
    
    for frustration in frustrations:
        text = f"{frustration['title']} {frustration.get('text', '')}".lower()
        for tool in tools_to_track:
            if tool in text:
                tool_mentions[tool].append(frustration)
    
    # Sort by number of complaints
    tool_problems = []
    for tool, mentions in tool_mentions.items():
        if len(mentions) > 0:
            tool_problems.append({
                'tool': tool.title(),
                'complaint_count': len(mentions),
                'top_complaint': mentions[0]['title'] if mentions else '',
                'opportunity': f"Better {tool.title()} alternative focusing on pain points"
            })
    
    return sorted(tool_problems, key=lambda x: x['complaint_count'], reverse=True)

def find_underserved_markets(frustrations):
    """Identify specific niches with problems"""
    
    market_keywords = {
        'E-commerce': ['shopify', 'woocommerce', 'product', 'inventory', 'shipping', 'orders'],
        'Real Estate': ['property', 'listing', 'tenant', 'rent', 'lease', 'mls'],
        'Healthcare': ['patient', 'appointment', 'medical', 'clinic', 'practice'],
        'Education': ['student', 'course', 'learning', 'teaching', 'classroom'],
        'Freelancers': ['freelance', 'client', 'invoice', 'contract', 'hourly'],
        'Agencies': ['agency', 'clients', 'projects', 'team', 'collaboration'],
        'SaaS': ['subscription', 'users', 'onboarding', 'churn', 'mrr'],
        'Content Creators': ['youtube', 'content', 'video', 'blog', 'social media']
    }
    
    market_problems = defaultdict(int)
    market_examples = defaultdict(list)
    
    for frustration in frustrations:
        text = f"{frustration['title']} {frustration.get('text', '')}".lower()
        for market, keywords in market_keywords.items():
            if any(keyword in text for keyword in keywords):
                market_problems[market] += 1
                market_examples[market].append(frustration['title'])
    
    return sorted([
        {
            'market': market,
            'problem_count': count,
            'examples': market_examples[market][:2]
        }
        for market, count in market_problems.items()
    ], key=lambda x: x['problem_count'], reverse=True)

# Load today's data
today = datetime.now().strftime('%Y-%m-%d')

try:
    # First try to load commercial frustrations (from improved scraper)
    with open(f'data/{today}/commercial_frustrations.json', 'r') as f:
        frustrations = json.load(f)
except FileNotFoundError:
    # Fall back to regular frustrations if commercial ones don't exist
    try:
        with open(f'data/{today}/reddit_frustrations.json', 'r') as f:
            frustrations = json.load(f)
    except FileNotFoundError:
        print("No frustration data found for today!")
        frustrations = []

if frustrations:
    print(f"Analyzing {len(frustrations)} frustrations...")
    
    # Find opportunities
    opportunities = find_solution_opportunities(frustrations)
    tool_problems = analyze_tool_problems(frustrations)
    underserved_markets = find_underserved_markets(frustrations)
    
    # Create comprehensive business opportunity report
    report_file = f'data/{today}/business_opportunities.md'
    with open(report_file, 'w') as f:
        f.write(f"# 🚀 Business Opportunity Report - {today}\n\n")
        f.write(f"*Analyzed {len(frustrations)} frustrations to find viable business opportunities*\n\n")
        
        # Top opportunities
        f.write("## 💡 Top Business Opportunities\n\n")
        
        if opportunities:
            for i, opp in enumerate(opportunities[:5], 1):
                f.write(f"### {i}. {opp['type']}\n")
                f.write(f"- **Frequency:** {opp['frequency']} similar problems found\n")
                f.write(f"- **Solution:** {opp['solution']}\n")
                f.write(f"- **Market Size:** {opp['market_size']}\n")
                f.write(f"- **Difficulty:** {opp['difficulty']}\n")
                f.write(f"- **Evidence:**\n")
                for example in opp['examples']:
                    f.write(f"  - [{example['title'][:80]}...]({example['url']})\n")
                f.write(f"- **Quick MVP Idea:** Start with the most requested feature and expand\n\n")
        else:
            f.write("*No clear opportunities found - may need more data*\n\n")
        
        # Tool problems (opportunities for alternatives)
        f.write("## 🛠️ Tools with Most Complaints (Alternative Opportunities)\n\n")
        
        if tool_problems:
            f.write("| Tool | Complaints | Opportunity |\n")
            f.write("|------|------------|-------------|\n")
            for tool in tool_problems[:10]:
                f.write(f"| {tool['tool']} | {tool['complaint_count']} | Build better alternative |\n")
            f.write("\n")
        
        # Underserved markets
        f.write("## 🎯 Underserved Markets\n\n")
        
        if underserved_markets:
            for market in underserved_markets[:5]:
                if market['problem_count'] > 2:
                    f.write(f"**{market['market']}** ({market['problem_count']} problems)\n")
                    for example in market['examples']:
                        f.write(f"- {example[:100]}...\n")
                    f.write("\n")
        
        # Actionable next steps
        f.write("## ✅ Recommended Next Steps\n\n")
        f.write("1. **Validate**: Pick top opportunity and create a landing page\n")
        f.write("2. **Research**: Check if solutions exist (Google, ProductHunt, etc.)\n")
        f.write("3. **Interview**: DM the Reddit users who posted these problems\n")
        f.write("4. **MVP**: Build simplest version that solves core problem\n")
        f.write("5. **Launch**: Share in the same subreddits where you found the problems\n\n")
        
        # Stats
        f.write("## 📊 Analysis Stats\n\n")
        f.write(f"- Total frustrations analyzed: {len(frustrations)}\n")
        f.write(f"- Business opportunities found: {len(opportunities)}\n")
        f.write(f"- Tools with problems: {len(tool_problems)}\n")
        f.write(f"- Markets identified: {len(underserved_markets)}\n")
    
    print(f"✅ Business opportunity report created: {report_file}")
    
    # Also create a simple CSV for tracking
    import csv
    csv_file = f'data/{today}/opportunities.csv'
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Opportunity Type', 'Frequency', 'Market Size', 'Difficulty', 'Solution'])
        for opp in opportunities:
            writer.writerow([
                opp['type'],
                opp['frequency'],
                opp['market_size'],
                opp['difficulty'],
                opp['solution']
            ])
    print(f"✅ CSV summary created: {csv_file}")

else:
    print("No data to analyze!")

print("\nDone! Check business_opportunities.md for actionable insights.")
