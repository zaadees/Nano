#!/usr/bin/env python3

import json
import os
import subprocess
import sys

def load_current_json():
    """Load the current version of index.json"""
    try:
        with open('washk12_jobs/index.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading current index.json: {e}")
        return None

def load_previous_json():
    """Load the previous committed version of index.json"""
    try:
        # Get the previous committed version using git show
        result = subprocess.run(
            ['git', 'show', 'HEAD~1:washk12_jobs/index.json'], 
            capture_output=True, 
            text=True, 
            check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error getting previous version: {e}")
        print(f"stderr: {e.stderr}")
        # If this is the first commit with this file, there's no previous version
        if "fatal: path 'washk12_jobs/index.json' does not exist in 'HEAD~1'" in e.stderr:
            print("No previous version found - this appears to be the first commit with this file")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing previous JSON: {e}")
        return None

def compare_jobs(current_data, previous_data):
    """Compare current and previous job listings"""
    if not current_data or not previous_data:
        print("Cannot compare - missing data")
        return
    
    current_jobs = {job['job_id']: job for job in current_data.get('jobs', [])}
    previous_jobs = {job['job_id']: job for job in previous_data.get('jobs', [])}
    
    # Find added, removed, and changed jobs
    added_jobs = [job_id for job_id in current_jobs if job_id not in previous_jobs]
    removed_jobs = [job_id for job_id in previous_jobs if job_id not in current_jobs]
    
    # For changed jobs, we need to compare the content
    changed_jobs = []
    for job_id in current_jobs:
        if job_id in previous_jobs:
            current_job = current_jobs[job_id]
            previous_job = previous_jobs[job_id]
            
            # Compare the jobs (excluding any timestamp fields that might change regularly)
            if current_job != previous_job:
                changed_jobs.append(job_id)
    
    # Print summary
    print(f"Job Changes Summary:")
    print(f"  Added: {len(added_jobs)} jobs")
    print(f"  Removed: {len(removed_jobs)} jobs")
    print(f"  Changed: {len(changed_jobs)} jobs")
    
    # Print details
    if added_jobs:
        print("\nAdded Jobs:")
        for job_id in added_jobs:
            job = current_jobs[job_id]
            print(f"  - {job_id}: {job.get('title', 'No title')} at {job.get('location', 'No location')}")
    
    if removed_jobs:
        print("\nRemoved Jobs:")
        for job_id in removed_jobs:
            job = previous_jobs[job_id]
            print(f"  - {job_id}: {job.get('title', 'No title')} at {job.get('location', 'No location')}")
    
    if changed_jobs:
        print("\nChanged Jobs:")
        for job_id in changed_jobs:
            job = current_jobs[job_id]
            print(f"  - {job_id}: {job.get('title', 'No title')} at {job.get('location', 'No location')}")

def main():
    print("Analyzing job changes...")
    current_data = load_current_json()
    previous_data = load_previous_json()
    
    if current_data and previous_data:
        compare_jobs(current_data, previous_data)
    else:
        print("Unable to compare job data - missing current or previous data")

if __name__ == "__main__":
    main()
