"""
LinkedIn Research Agent - Shows real-time thought process and accesses LinkedIn data
"""
import os
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from openai import OpenAI
from linkedin_rapidapi_client import LinkedInRapidAPIClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
# Note: the newest OpenAI model is "gpt-4o" which was released May 13, 2024
GPT_MODEL = "gpt-4o"


class ResearchStep:
    """A research step with detailed tracking of agent's thought process"""
    
    def __init__(self, description: str, reasoning: Optional[str] = None):
        """
        Initialize a research step
        
        Args:
            description: What this step does
            reasoning: Why this step is taken (optional)
        """
        self.description = description
        self.reasoning = reasoning
        self.status = "in_progress"
        self.result = None
        self.start_time = datetime.now()
        self.end_time = None
        self.confidence = None
        
    def complete(self, success: bool, result: Any = None, confidence: Optional[float] = None):
        """
        Mark the step as complete with results
        
        Args:
            success: Whether the step was successful
            result: Result of the step
            confidence: Confidence level in the result (0.0 to 1.0)
        """
        self.status = "completed" if success else "failed"
        self.result = result
        self.end_time = datetime.now()
        self.confidence = confidence
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        duration = None
        if self.end_time and self.start_time:
            duration = (self.end_time - self.start_time).total_seconds()
        
        return {
            "description": self.description,
            "reasoning": self.reasoning,
            "status": self.status,
            "result": self.result,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": duration,
            "confidence": self.confidence
        }


class LinkedInResearchAgent:
    """
    LinkedIn research agent that shows its thought process
    while accessing real LinkedIn data from RapidAPI
    """
    
    def __init__(self):
        """Initialize the LinkedIn researcher"""
        self.steps = []
        self.profiles = []
        self.insights = []
        self.company_info = None
        self.summary = None
        self.linkedin_client = LinkedInRapidAPIClient()
        
    async def research(self, query: str) -> Dict[str, Any]:
        """
        Perform LinkedIn research with transparent thought process
        
        Args:
            query: User research query
            
        Returns:
            Research results with detailed thought process
        """
        try:
            # Step 1: Initialize the research process
            init_step = self._add_step(
                "Initializing LinkedIn research", 
                "Setting up the research process and preparing API connections."
            )
            init_step.complete(True)
            
            # Step 2: Analyze the query to understand research requirements
            analysis_step = self._add_step(
                "Analyzing query", 
                "Breaking down the query to identify companies, roles, and technologies."
            )
            
            query_analysis = await self._analyze_query(query)
            
            company_name = query_analysis.get("company")
            roles = query_analysis.get("roles", [])
            technologies = query_analysis.get("technologies", [])
            
            analysis_step.complete(True, {
                "company": company_name,
                "roles": roles,
                "technologies": technologies
            })
            
            # Step 3: Research company if specified
            if company_name:
                company_step = self._add_step(
                    f"Researching company: {company_name}",
                    f"Gathering information about {company_name} from LinkedIn."
                )
                
                company_info = self.linkedin_client.get_company_info(company_name)
                
                if company_info:
                    company_step.complete(True, company_info)
                    self.company_info = company_info
                else:
                    company_step.complete(False, {
                        "error": f"Could not find verified information for {company_name}"
                    })
            
            # Step 4: Search for professionals
            search_step = self._add_step(
                "Searching for professionals", 
                "Finding relevant professionals based on query criteria."
            )
            
            # Determine search query from roles or original query
            search_query = roles[0] if roles else query
            
            # Search for people
            if company_name:
                profiles = self.linkedin_client.search_people(search_query, company_name)
            else:
                profiles = self.linkedin_client.search_people(search_query)
                
            if profiles:
                search_step.complete(True, {"profiles_found": len(profiles)})
                self.profiles = profiles
            else:
                search_step.complete(False, {"error": "No matching profiles found"})
                
                # Try a fallback search with just the original query
                fallback_step = self._add_step(
                    "Attempting broader search",
                    "Initial search returned no results. Trying with broader criteria."
                )
                
                fallback_profiles = self.linkedin_client.search_people(query)
                
                if fallback_profiles:
                    fallback_step.complete(True, {"profiles_found": len(fallback_profiles)})
                    self.profiles = fallback_profiles
                else:
                    fallback_step.complete(False, {"error": "No profiles found in fallback search"})
            
            # Step 5: Generate insights from the profiles
            if self.profiles:
                insight_step = self._add_step(
                    "Analyzing professional profiles",
                    "Examining profiles to identify patterns and insights."
                )
                
                insights = await self._generate_insights(self.profiles, company_name, roles)
                insight_step.complete(True, {"insights_generated": len(insights)})
                self.insights = insights
            
            # Step 6: Create a comprehensive summary
            summary_step = self._add_step(
                "Creating research summary",
                "Synthesizing findings into a comprehensive research summary."
            )
            
            summary = await self._create_summary(query)
            summary_step.complete(True)
            self.summary = summary
            
            # Return the research results
            return {
                "query": query,
                "steps": [step.to_dict() for step in self.steps],
                "company": self.company_info,
                "profiles": self.profiles,
                "insights": self.insights,
                "summary": self.summary
            }
            
        except Exception as e:
            logger.error(f"Error in LinkedIn research: {str(e)}")
            error_step = self._add_step(
                "Error in research process",
                f"An error occurred: {str(e)}"
            )
            error_step.complete(False, {"error_message": str(e)})
            
            return {
                "query": query,
                "steps": [step.to_dict() for step in self.steps],
                "error": str(e)
            }
    
    def _add_step(self, description: str, reasoning: Optional[str] = None) -> ResearchStep:
        """Add a research step and return it"""
        step = ResearchStep(description, reasoning)
        self.steps.append(step)
        return step
    
    async def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze the query using GPT to extract key information"""
        prompt = "Analyze the following LinkedIn research query and extract key information:\n\n"
        prompt += f"Query: \"{query}\"\n\n"
        prompt += "Extract the following information:\n"
        prompt += "1. Target company name (if any)\n"
        prompt += "2. Professional roles of interest (e.g., software engineer, product manager)\n"
        prompt += "3. Technologies or skills mentioned (e.g., Python, machine learning)\n\n"
        prompt += "Format the response as a JSON object with these keys:\n"
        prompt += "- company: The target company name (null if none specified)\n"
        prompt += "- roles: Array of professional roles mentioned\n"
        prompt += "- technologies: Array of technologies or skills mentioned"
        
        try:
            response = openai_client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": "You are a professional research assistant that extracts structured information from queries."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse the JSON response
            analysis = json.loads(response.choices[0].message.content)
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing query with GPT: {e}")
            # Return a basic analysis if GPT fails
            return {
                "company": None,
                "roles": [query],
                "technologies": []
            }
    
    async def _generate_insights(self, profiles: List[Dict[str, Any]], 
                                company: Optional[str], roles: List[str]) -> List[str]:
        """Generate insights about the profiles using GPT"""
        # Format profiles for GPT analysis
        profiles_text = []
        for i, profile in enumerate(profiles, 1):
            profile_text = f"{i}. {profile.get('name', 'Unknown')}\n"
            profile_text += f"   Title: {profile.get('title', 'N/A')}\n" 
            profile_text += f"   Company: {profile.get('company', 'N/A')}\n"
            profile_text += f"   Location: {profile.get('location', 'N/A')}\n"
            profile_text += f"   Expertise: {', '.join(profile.get('expertise', []))}\n"
            profiles_text.append(profile_text)
        
        profiles_str = "\n".join(profiles_text)
        
        company_context = f"For company: {company}" if company else ""
        roles_context = f"For roles: {', '.join(roles)}" if roles else "" 
        
        prompt = "Analyze the following LinkedIn profiles and generate insights:\n\n"
        prompt += f"Profiles:\n{profiles_str}\n\n"
        prompt += f"{company_context}\n" if company_context else ""
        prompt += f"{roles_context}\n" if roles_context else ""
        prompt += "\nGenerate 3-5 meaningful insights about these professionals. Focus on:\n"
        prompt += "1. Common skills or qualifications\n"
        prompt += "2. Career trajectories\n"
        prompt += "3. Industry patterns\n"
        prompt += "4. Any other notable patterns\n\n"
        prompt += "Format your response as a JSON array of insight strings."
        
        try:
            response = openai_client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": "You are a professional LinkedIn researcher who identifies patterns and insights from profiles."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse the JSON response
            insights_data = json.loads(response.choices[0].message.content)
            
            # Extract insights array from the response
            if isinstance(insights_data, list):
                return insights_data
            elif "insights" in insights_data:
                return insights_data["insights"]
            else:
                return list(insights_data.values()) if isinstance(insights_data, dict) else []
            
        except Exception as e:
            logger.error(f"Error generating insights with GPT: {e}")
            return ["Unable to generate insights due to an error."]
    
    async def _create_summary(self, query: str) -> str:
        """Create a comprehensive research summary using GPT"""
        # Format profiles
        profiles_text = []
        for i, profile in enumerate(self.profiles[:5], 1):  # Limit to 5 profiles
            profile_text = f"{i}. {profile.get('name', 'Unknown')}\n"
            profile_text += f"   Title: {profile.get('title', 'N/A')}\n"
            profile_text += f"   Company: {profile.get('company', 'N/A')}\n"
            profile_text += f"   Location: {profile.get('location', 'N/A')}\n"
            profile_text += f"   Expertise: {', '.join(profile.get('expertise', []))}\n"
            profiles_text.append(profile_text)
        
        # Format company info
        company_text = ""
        if self.company_info:
            company_text = f"""
            Company Information:
            Name: {self.company_info.get('name', 'N/A')}
            Industry: {self.company_info.get('industry', 'N/A')}
            Location: {self.company_info.get('location', 'N/A')}
            Description: {self.company_info.get('description', 'N/A')}
            """
        
        # Format insights
        insights_text = "\n".join([f"- {insight}" for insight in self.insights])
        
        prompt = "Create a comprehensive LinkedIn research summary based on the following:\n\n"
        prompt += f"Original Query:\n{query}\n\n"
        
        if company_text:
            prompt += f"{company_text}\n\n"
        
        if profiles_text:
            prompt += f"Professionals Found:\n{chr(10).join(profiles_text)}\n\n"
        else:
            prompt += "Professionals Found:\nNo profiles found.\n\n"
        
        if insights_text:
            prompt += f"Insights:\n{insights_text}\n\n"
        else:
            prompt += "Insights:\nNo insights available.\n\n"
        
        prompt += "Create a detailed research summary in Markdown format that includes:\n"
        prompt += "1. A summary of the research request\n"
        prompt += "2. Company overview (if applicable)\n"
        prompt += "3. Key professionals found\n"
        prompt += "4. Patterns and insights\n"
        prompt += "5. Recommendations for networking or further research\n\n"
        prompt += "Make the summary actionable and insightful for a business professional."
        
        try:
            response = openai_client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": "You are a professional LinkedIn researcher who creates comprehensive summaries of research findings."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error creating summary with GPT: {e}")
            return "Unable to generate a summary due to an error."


async def research_linkedin(query: str) -> Dict[str, Any]:
    """
    Perform LinkedIn research with transparent process
    
    Args:
        query: Research query
        
    Returns:
        Research results with all steps and thought processes
    """
    agent = LinkedInResearchAgent()
    return await agent.research(query)
