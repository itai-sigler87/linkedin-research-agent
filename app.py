"""
LinkedIn Researcher - Flask web application
"""
import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from flask import Flask, render_template, request, jsonify, redirect, url_for, abort
from markupsafe import Markup
import markdown

from db import db, init_db
from models import ResearchQuery, ResearchStep, LinkedInProfile, Insight
from simple_linkedin_agent import research_linkedin
from linkedin_api import linkedin_api

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "linkedin-researcher-secret-key")

# Initialize database
init_db(app)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Markdown filter for templates
@app.template_filter('markdown')
def render_markdown(text):
    return Markup(markdown.markdown(text))


# Helper functions
def get_api_keys() -> Dict[str, bool]:
    """
    Get API key status for UI display
    
    Returns:
        Dictionary of API key statuses
    """
    return {
        "openai": bool(os.environ.get("OPENAI_API_KEY")),
        "rapidapi": bool(os.environ.get("RAPIDAPI_KEY")),
        "linkedin": bool(os.environ.get("LINKEDIN_EMAIL") and os.environ.get("LINKEDIN_PASSWORD"))
    }


def start_research_task(query: str) -> int:
    """
    Start a new research task
    
    Args:
        query: Research query
        
    Returns:
        Research ID
    """
    # Create a research record
    research = ResearchQuery()
    research.query = query
    research.status = "pending"
    db.session.add(research)
    db.session.commit()
    
    # Return the ID for status polling
    return research.id


async def run_research_task(research_id: int) -> None:
    """
    Run a research task asynchronously
    
    Args:
        research_id: Research task ID
    """
    try:
        # Get the research record
        research = db.session.get(ResearchQuery, research_id)
        if not research:
            logger.error(f"Research not found: {research_id}")
            return
            
        # Update status
        research.status = "in_progress"
        db.session.commit()
        
        # Run research
        query = research.query
        results = await research_linkedin(query)
        
        # Process results
        if "error" in results:
            research.status = "failed"
            research.summary = f"Research failed: {results['error']}"
            db.session.commit()
            return
            
        # Update research
        research.status = "completed"
        research.summary = results.get("summary", "")
        research.updated_at = datetime.now()
        
        # Save steps
        for step_data in results.get("steps", []):
            step = ResearchStep()
            step.research_id = research.id
            step.type = step_data.get("type", "analysis")
            step.description = step_data.get("description", "")
            step.reasoning = step_data.get("reasoning", "")
            step.status = step_data.get("status", "completed")
            step.confidence = step_data.get("confidence")
            step.duration = step_data.get("duration")
            
            if step_data.get("result") is not None:
                if isinstance(step_data["result"], (dict, list)):
                    step.result = json.dumps(step_data["result"])
                else:
                    step.result = str(step_data["result"])
                    
            db.session.add(step)
        
        # Save profiles
        for profile_data in results.get("profiles", []):
            profile = LinkedInProfile()
            profile.research_id = research.id
            profile.name = profile_data.get("name", "")
            profile.title = profile_data.get("title", "")
            profile.company = profile_data.get("company", "")
            profile.location = profile_data.get("location", "")
            profile.linkedin_url = profile_data.get("linkedin_url", "")
            profile.image_url = profile_data.get("image_url", "")
            
            if "expertise" in profile_data and profile_data["expertise"]:
                profile.expertise = json.dumps(profile_data["expertise"])
                
            db.session.add(profile)
        
        # Save insights
        for insight in results.get("insights", []):
            insight_record = Insight()
            insight_record.research_id = research.id
            insight_record.text = insight
            db.session.add(insight_record)
            
        # Commit all changes
        db.session.commit()
        logger.info(f"Research completed: {research_id}")
            
    except Exception as e:
        logger.error(f"Error running research task: {str(e)}")
        try:
            research = db.session.get(ResearchQuery, research_id)
            if research:
                research.status = "failed"
                research.summary = f"Research failed: {str(e)}"
                db.session.commit()
        except Exception:
            pass


# Routes
@app.route('/')
def index():
    """Home page"""
    api_keys = get_api_keys()
    return render_template("index.html", api_keys=api_keys)


@app.route('/research', methods=['GET', 'POST'])
def research():
    """Research page"""
    if request.method == 'POST':
        query = request.form.get('query', '')
        if query:
            # Start the research task
            research_id = start_research_task(query)
            
            # Run the task in the background
            asyncio.create_task(run_research_task(research_id))
            
            # Redirect to research results page
            return redirect(url_for('research_results', research_id=research_id))
        else:
            return render_template("research.html", error="Please enter a research query.")
    
    return render_template("research.html")


@app.route('/research/<int:research_id>')
def research_results(research_id):
    """Research results page"""
    research = db.session.get(ResearchQuery, research_id)
    
    if not research:
        abort(404)
        
    profiles = db.session.query(LinkedInProfile).filter_by(research_id=research_id).all()
    steps = db.session.query(ResearchStep).filter_by(research_id=research_id).all()
    insights = db.session.query(Insight).filter_by(research_id=research_id).all()
    
    return render_template(
        "research_results.html",
        research=research,
        profiles=profiles,
        steps=steps,
        insights=insights
    )


@app.route('/saved-research')
def saved_research():
    """Saved research page"""
    research_items = db.session.query(ResearchQuery).order_by(ResearchQuery.created_at.desc()).all()
    return render_template("saved_research.html", research_items=research_items)


@app.route('/api/research/<int:research_id>')
def api_research_status(research_id):
    """API endpoint for research status"""
    research = db.session.get(ResearchQuery, research_id)
    
    if not research:
        abort(404)
    
    # Get related data
    profiles = db.session.query(LinkedInProfile).filter_by(research_id=research_id).all()
    steps = db.session.query(ResearchStep).filter_by(research_id=research_id).all()
    insights = db.session.query(Insight).filter_by(research_id=research_id).all()
    
    # Format profiles with expertise as list
    profiles_data = []
    for profile in profiles:
        profile_dict = profile.to_dict()
        if profile.expertise:
            try:
                profile_dict["expertise"] = json.loads(profile.expertise)
            except:
                profile_dict["expertise"] = []
        else:
            profile_dict["expertise"] = []
        profiles_data.append(profile_dict)
    
    # Prepare response
    response = {
        "id": research.id,
        "query": research.query,
        "status": research.status,
        "summary": research.summary,
        "created_at": research.created_at.isoformat() if research.created_at else None,
        "updated_at": research.updated_at.isoformat() if research.updated_at else None,
        "profiles": profiles_data,
        "steps": [step.to_dict() for step in steps],
        "insights": [insight.to_dict() for insight in insights]
    }
    
    return jsonify(response)


@app.errorhandler(404)
def page_not_found(e):
    """404 error handler"""
    return render_template("error.html", message="Page not found"), 404


@app.errorhandler(500)
def server_error(e):
    """500 error handler"""
    return render_template("error.html", message="Server error occurred. Please try again."), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
