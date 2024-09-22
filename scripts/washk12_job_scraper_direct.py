#!/usr/bin/env python3

"""
Washington County School District Job Scraper

This script downloads job postings and saves them to a JSON file with timestamp.
Debug output can be enabled by passing --debug as a command line argument.
Use --index to save as index.json (overwriting any existing file).
"""

import re
import json
import time
import os
import sys
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# Check command line arguments
DEBUG = "--debug" in sys.argv
INDEX_MODE = "--index" in sys.argv


def extract_job_details(html_content, index):
    """Extract job details from HTML content."""
    # Save individual job HTML for debugging if it's one of the first few jobs
    if DEBUG and index <= 3:
        # Create washk12_jobs directory if it doesn't exist
        output_dir = "washk12_jobs"
        os.makedirs(output_dir, exist_ok=True)
        
        job_html_filename = os.path.join(output_dir, f"job_{index}_raw.html")
        with open(job_html_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    # Parse HTML
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Get text content
    all_text = soup.get_text(strip=True)
    
    # Extract job title from table.title
    title = ""
    title_table = soup.find('table', class_='title')
    if title_table and title_table.find('td', id='wrapword'):
        title = title_table.find('td', id='wrapword').get_text(strip=True)
    
    # Extract job ID from the JobID text or apply button
    job_id = f"job_{index}"
    
    # Method 1: Look for JobID in text
    job_id_span = soup.find(string=lambda text: text and 'JobID:' in text)
    if job_id_span:
        job_id_match = re.search(r'JobID:\s*(\d+)', job_id_span)
        if job_id_match:
            job_id = job_id_match.group(1)
    
    # Method 2: Look for apply button
    apply_button = soup.find('input', {'value': ' Apply ', 'class': 'screenOnly ApplyButton'})
    if apply_button and 'onclick' in apply_button.attrs:
        onclick = apply_button['onclick']
        id_match = re.search(r"applyFor\('(\d+)'", onclick)
        if id_match:
            job_id = id_match.group(1)
    
    # Look for span elements with class 'label' for field names
    fields = {}
    
    # Find all span elements with class 'label'
    label_spans = soup.find_all('span', class_='label')
    
    # Find all li elements that contain label spans
    list_items = soup.find_all('li')
    for li in list_items:
        label_span = li.find('span', class_='label')
        if label_span:
            field_name = label_span.get_text(strip=True).replace(':', '')
            # Find normal spans within this li
            normal_spans = li.find_all('span', class_='normal')
            if normal_spans:
                # Combine all normal spans text
                field_value = ' '.join(span.get_text(strip=True) for span in normal_spans)
                fields[field_name] = field_value
    
    # Extract common job fields from the fields dictionary or using regex
    position_type = fields.get('Position Type', '')
    if not position_type:
        position_type = extract_field(all_text, r'Position Type:?\s*(.*?)(?:\n|$)')
    
    location = fields.get('Location', '')
    if not location:
        location = extract_field(all_text, r'Location:?\s*(.*?)(?:\n|$)')
    
    date_posted = fields.get('Date Posted', '')
    if not date_posted:
        date_posted = extract_field(all_text, r'Date Posted:?\s*(.*?)(?:\n|$)')
    
    closing_date = fields.get('Closing Date', '')
    if not closing_date:
        closing_date = extract_field(all_text, r'Closing Date:?\s*(.*?)(?:\n|$)')
    
    # Look for additional fields
    date_available = fields.get('Date Available', '')
    if not date_available:
        date_available = extract_field(all_text, r'Date Available:?\s*(.*?)(?:\n|$)')
    
    status = fields.get('Status', '')
    if not status:
        status = extract_field(all_text, r'Status:?\s*(.*?)(?:\n|$)')
    
    requirements = fields.get('Minimum Requirements', '')
    if not requirements:
        requirements = extract_field(all_text, r'Minimum Requirements:?\s*(.*?)(?:\n|$)')
    
    salary_info = fields.get('Salary', '')
    if not salary_info:
        salary_info = extract_field(all_text, r'Salary:?\s*(.*?)(?:\n|$)')
        if not salary_info:
            # Look for salary schedule mentions
            salary_match = re.search(r'salary schedule|salary is', all_text, re.IGNORECASE)
            if salary_match:
                # Extract a reasonable amount of text around the salary mention
                start = max(0, salary_match.start() - 50)
                end = min(len(all_text), salary_match.end() + 150)
                salary_info = all_text[start:end].strip()
    
    # Extract FTE if available
    fte = fields.get('FTE', '')
    if not fte and status:
        fte_match = re.search(r'(\d+(?:\.\d+)?\s*FTE)', status, re.IGNORECASE)
        if fte_match:
            fte = fte_match.group(1)
    
    # Extract endorsements and license requirements
    endorsements = fields.get('Endorsements Required', '')
    if not endorsements:
        endorsements = extract_field(all_text, r'Endorsements?:?\s*(.*?)(?:\n|$)')
        if not endorsements and requirements:
            # Look for endorsement mentions in requirements
            end_match = re.search(r'endorsements?', requirements, re.IGNORECASE)
            if end_match:
                # Extract a reasonable amount of text around the endorsement mention
                start = max(0, end_match.start() - 20)
                end = min(len(requirements), end_match.end() + 100)
                endorsements = requirements[start:end].strip()
    
    license_req = fields.get('License Requirements', '')
    if not license_req:
        license_req = extract_field(all_text, r'License Requirements?:?\s*(.*?)(?:\n|$)')
        if not license_req and requirements:
            # Look for license mentions in requirements
            lic_match = re.search(r'license', requirements, re.IGNORECASE)
            if lic_match:
                # Extract a reasonable amount of text around the license mention
                start = max(0, lic_match.start() - 20)
                end = min(len(requirements), lic_match.end() + 100)
                license_req = requirements[start:end].strip()
    
    # Extract description - often in a span with ID starting with 'DescriptionText'
    description = ""
    
    # Method 1: Look for span with ID starting with DescriptionText
    desc_span = soup.find('span', id=lambda x: x and x.startswith('DescriptionText'))
    if desc_span:
        description = desc_span.get_text(strip=True)
    
    # Method 2: Look for Additional Information in fields
    elif 'Additional Information' in fields:
        description = fields['Additional Information']
    
    # Method 3: Look for any span that might contain a description
    else:
        # Find spans that might contain a job description
        for span in soup.find_all('span'):
            if span.get('id') and 'Text' in span.get('id'):
                span_text = span.get_text(strip=True)
                if len(span_text) > 100:  # Likely a description if it's long
                    description = span_text
                    break
    
    # Find attachments
    attachments = []
    attachments_div = soup.find('div', class_='AppliTrackJobPostingAttachments')
    if attachments_div:
        for link in attachments_div.find_all('a'):
            attachments.append({
                'text': link.get_text(strip=True),
                'url': link.get('href', '')
            })
    
    # Print debug info for the first few jobs
    if DEBUG and index <= 3:
        print(f"\nDebug info for job {index}:")
        print(f"  Title: {title}")
        print(f"  Job ID: {job_id}")
        print(f"  Found {len(label_spans)} label spans")
        print(f"  Fields extracted: {list(fields.keys())}")
        print(f"  Has description: {'Yes' if description else 'No'}")
        print(f"  Has attachments: {'Yes' if attachments else 'No'}")
        
        # Print the first few label spans for debugging
        if label_spans:
            print("  Sample label spans:")
            for i, span in enumerate(label_spans[:3]):
                print(f"    {i+1}. {span.get_text(strip=True)}")
    
    # Create job data dictionary with all available fields
    job_data = {
        "job_id": job_id,
        "title": title,
        "position_type": position_type,
        "location": location,
        "date_posted": date_posted,
        "date_available": date_available,
        "closing_date": closing_date,
        "status": status,
        "minimum_requirements": requirements,
        "salary_information": salary_info,
        "description": description[:500] + ("..." if len(description) > 500 else ""),
        "attachments": attachments,
        "url": f"https://www.applitrack.com/washk12/onlineapp/default.aspx?AppliTrackJobId={job_id}" 
               if not job_id.startswith('job_') else 
               f"https://www.applitrack.com/washk12/onlineapp/default.aspx?all=1"
    }
    
    # Add optional fields if they have values
    if fte:
        job_data["fte"] = fte
    
    if endorsements:
        job_data["endorsements_required"] = endorsements
    
    if license_req:
        job_data["license_requirements"] = license_req
    
    # Print debug info for the first few jobs
    if DEBUG and index <= 3:
        print(f"\nDebug info for job {index}:")
        print(f"  Title: {title}")
        print(f"  Job ID: {job_id}")
        print(f"  Position Type: {position_type}")
        print(f"  Location: {location}")
        print(f"  Date Posted: {date_posted}")
        print(f"  Closing Date: {closing_date}")
        print(f"  Found {len(fields)} fields")
        print(f"  Fields: {', '.join(fields.keys())}")
        print(f"  Has description: {'Yes' if description else 'No'}")
        print(f"  Has attachments: {'Yes' if attachments else 'No'}")
    
    return job_data


def extract_field(text, pattern):
    """Extract a field from text using regex."""
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def download_jobs():
    """Download job postings and extract details."""
    print("Downloading Washington County School District job listings...")
    
    url = "https://www.applitrack.com/washk12/onlineapp/jobpostings/Output.asp?all=1&"
    
    # Set up request headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
    }
    
    # Download content
    response = requests.get(url, headers=headers)
    content = response.text
    
    # Save raw content to file for debugging
    if DEBUG:
        # Create washk12_jobs directory if it doesn't exist
        output_dir = "washk12_jobs"
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_filename = os.path.join(output_dir, f"washk12_raw_{timestamp}.html")
        with open(raw_filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Saved raw HTML content to {raw_filename} for debugging")
    
    # Extract all document.write statements from the scripts
    doc_writes = re.findall(r'document\.write\(\'(.*?)\'\);', content, re.DOTALL)
    
    # Combine all document.write contents into a single HTML string
    combined_html = ''.join(doc_writes)
    combined_html = combined_html.replace("\\'", "'").replace('\\"', '"')
    
    # Save the combined HTML for debugging
    if DEBUG:
        combined_filename = os.path.join(output_dir, f"washk12_combined_{timestamp}.html")
        with open(combined_filename, 'w', encoding='utf-8') as f:
            f.write(combined_html)
    
    # Parse the combined HTML
    soup = BeautifulSoup(combined_html, 'lxml')
    
    # Find all job listings - they typically have a table with class 'title'
    job_blocks = []
    
    # Find all tables with class 'title' - these contain job titles and IDs
    title_tables = soup.find_all('table', class_='title')
    
    for table in title_tables:
        # Find the parent ul.postingsList that contains the full job listing
        parent_ul = table.find_parent('ul', class_='postingsList')
        if parent_ul:
            job_blocks.append(str(parent_ul))
    
    print(f"Found {len(job_blocks)} job postings")
    
    if not job_blocks:
        print("No job postings found.")
        return []
    
    print(f"Found {len(job_blocks)} job postings")
    
    # Process job postings
    jobs = []
    for i, block in enumerate(job_blocks, 1):
        job_data = extract_job_details(block, i)
        jobs.append(job_data)
        
        # Log progress sparingly
        if i == 1 or i == len(job_blocks) or i % 25 == 0:
            print(f"Processed {i}/{len(job_blocks)} jobs")
    
    return jobs


def save_jobs_to_json(jobs):
    """Save jobs to a JSON file with timestamp in the washk12_jobs directory."""
    if not jobs:
        return ""
    
    # Create washk12_jobs directory if it doesn't exist
    output_dir = "washk12_jobs"
    os.makedirs(output_dir, exist_ok=True)
    
    # Get current timestamp for metadata
    timestamp = datetime.now()
    date_str = timestamp.strftime("%Y-%m-%d")
    unix_timestamp = int(time.time())
    
    # Determine filename based on INDEX_MODE flag
    if INDEX_MODE:
        filename = os.path.join(output_dir, "index.json")
    else:
        # Add time to filename when not in index mode
        time_str = timestamp.strftime("%H-%M-%S")
        filename = os.path.join(output_dir, f"washk12_jobs_{date_str}_{time_str}_{unix_timestamp}.json")
    
    # Create data structure with metadata
    data = {
        "source": "Washington County School District",
        "date": date_str,
        "job_count": len(jobs),
        "jobs": jobs
    }
    
    # Save to file
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    return filename


def analyze_html_structure(html_content):
    """Analyze the HTML structure to help debug extraction issues."""
    if not DEBUG:
        return
        
    print("\nAnalyzing HTML structure:")
    
    # Check for common job-related elements
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Look for different types of elements
    elements = {
        'ul.postingsList': soup.select('ul.postingsList'),
        'table.title': soup.select('table.title'),
        'span.label': soup.select('span.label'),
        'span.normal': soup.select('span.normal'),
        'div.AppliTrackJobPostingAttachments': soup.select('div.AppliTrackJobPostingAttachments'),
        'JobID mentions': soup.find_all(string=lambda t: t and 'JobID:' in t)
    }
    
    for name, found in elements.items():
        print(f"  Found {len(found)} {name} elements")
    
    # Check for document.write patterns
    doc_writes = re.findall(r'document\.write\(\'(.*?)\'\);', html_content, re.DOTALL)
    print(f"  Found {len(doc_writes)} document.write statements")
    
    # Check for script tags
    scripts = soup.find_all('script')
    print(f"  Found {len(scripts)} script tags")
    
    # Look at the first few document.write contents if any
    if doc_writes and len(doc_writes) > 0:
        print("\nSample document.write content:")
        sample = doc_writes[0][:200] + "..." if len(doc_writes[0]) > 200 else doc_writes[0]
        print(f"  {sample}")
        
        # Try to parse the document.write content
        write_soup = BeautifulSoup(doc_writes[0].replace("\\'", "'"), 'lxml')
        postings = write_soup.select('ul.postingsList')
        print(f"  Found {len(postings)} postingsList elements in the first document.write")

def main():
    """Main function to download and save job listings."""
    if DEBUG:
        print("Running in DEBUG mode - additional information will be displayed")
    if INDEX_MODE:
        print("Running in INDEX mode - output will be saved as index.json")
    
    jobs = download_jobs()
    
    # Try to analyze the raw HTML structure
    if DEBUG:
        try:
            # Create washk12_jobs directory if it doesn't exist
            output_dir = "washk12_jobs"
            os.makedirs(output_dir, exist_ok=True)
            
            # Find the most recent raw HTML file in the washk12_jobs directory
            raw_files = [f for f in os.listdir(output_dir) if f.startswith('washk12_raw_') and f.endswith('.html')]
            if raw_files:
                latest_file = os.path.join(output_dir, max(raw_files))
                with open(latest_file, 'r', encoding='utf-8') as f:
                    raw_html = f.read()
                    analyze_html_structure(raw_html)
        except Exception as e:
            print(f"Could not analyze HTML structure: {e}")
    
    if jobs:
        # Print a sample job to verify fields
        if DEBUG and len(jobs) > 0:
            print("\nSample job data:")
            sample_job = jobs[0]
            for key, value in sample_job.items():
                if key == "text_content" and len(value) > 100:
                    print(f"  {key}: {value[:100]}...")
                else:
                    print(f"  {key}: {value}")
            print()
        
        filename = save_jobs_to_json(jobs)
        print(f"Successfully saved {len(jobs)} jobs to {filename}")
    else:
        print("No jobs found.")


if __name__ == "__main__":
    main()
