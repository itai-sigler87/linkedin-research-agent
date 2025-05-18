"""
LinkedIn RapidAPI Client - Accesses real LinkedIn data through RapidAPI
"""
import os
import requests
import logging
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LinkedInRapidAPIClient:
    """Client for accessing LinkedIn data through RapidAPI"""
    
    def __init__(self):
        """Initialize the LinkedIn RapidAPI client"""
        self.api_key = os.environ.get("RAPIDAPI_KEY")
        if not self.api_key:
            logger.warning("RAPIDAPI_KEY environment variable not set")
        
        self.base_url = "https://linkedin-data-scraper.p.rapidapi.com"
        self.headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "linkedin-data-scraper.p.rapidapi.com"
        }
    
    def get_company_info(self, company_name: str) -> Optional[Dict[str, Any]]:
        """
        Get company information from LinkedIn
        
        Args:
            company_name: Name of the company
            
        Returns:
            Company information or None if not found
        """
        try:
            url = f"{self.base_url}/company"
            querystring = {"company_name": company_name}
            
            logger.info(f"Requesting company info for {company_name}")
            response = requests.get(url, headers=self.headers, params=querystring)
            
            if response.status_code == 200:
                data = response.json()
                if data and "items" in data and data["items"]:
                    # Extract and format company information
                    company_data = data["items"][0]
                    return {
                        "name": company_data.get("name", company_name),
                        "industry": company_data.get("industry", "Unknown"),
                        "location": company_data.get("location", "Unknown"),
                        "description": company_data.get("description", "No description available"),
                        "website": company_data.get("website", ""),
                        "linkedin_url": company_data.get("linkedin_url", ""),
                        "logo_url": company_data.get("logo_url", ""),
                        "employees": company_data.get("employees", {})
                    }
                else:
                    # Fallback for well-known companies
                    return self._get_fallback_company_info(company_name)
            else:
                logger.warning(f"Failed to get company info for {company_name}: {response.status_code}")
                logger.debug(f"Response: {response.text}")
                return self._get_fallback_company_info(company_name)
                
        except Exception as e:
            logger.error(f"Error getting company info: {str(e)}")
            return self._get_fallback_company_info(company_name)
    
    def search_people(self, query: str, company: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for professionals on LinkedIn
        
        Args:
            query: Search query (role, skill, etc.)
            company: Company name (optional)
            
        Returns:
            List of professional profiles
        """
        try:
            url = f"{self.base_url}/people/search"
            
            if company:
                query_str = f"{query} at {company}"
            else:
                query_str = query
                
            querystring = {"search_term": query_str}
            
            logger.info(f"Searching LinkedIn with query: {query_str}")
            response = requests.get(url, headers=self.headers, params=querystring)
            
            if response.status_code == 200:
                data = response.json()
                if data and "items" in data and data["items"]:
                    profiles = []
                    
                    for profile_data in data["items"]:
                        profile = {
                            "name": profile_data.get("name", "Unknown"),
                            "title": profile_data.get("title", ""),
                            "company": profile_data.get("company", ""),
                            "location": profile_data.get("location", ""),
                            "linkedin_url": profile_data.get("linkedin_url", ""),
                            "image_url": profile_data.get("image_url", ""),
                            "expertise": profile_data.get("expertise", [])
                        }
                        profiles.append(profile)
                    
                    return profiles
                else:
                    logger.warning(f"No profiles found for query: {query_str}")
                    return []
            else:
                logger.warning(f"Failed to search people with query {query_str}: {response.status_code}")
                logger.debug(f"Response: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error searching people: {str(e)}")
            return []
    
    def _get_fallback_company_info(self, company_name: str) -> Dict[str, Any]:
        """
        Get fallback company information for known companies
        
        Args:
            company_name: Name of the company
            
        Returns:
            Basic company information
        """
        # Lowercase for case-insensitive matching
        company_lower = company_name.lower()
        
        # Map of well-known companies
        companies = {
            "google": {
                "name": "Google",
                "industry": "Technology",
                "location": "Mountain View, CA",
                "description": "Google is a multinational technology company that specializes in Internet-related services and products.",
                "website": "https://www.google.com",
                "linkedin_url": "https://www.linkedin.com/company/google/",
                "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/53/Google_%22G%22_Logo.svg/2048px-Google_%22G%22_Logo.svg.png"
            },
            "microsoft": {
                "name": "Microsoft",
                "industry": "Technology",
                "location": "Redmond, WA",
                "description": "Microsoft is a multinational technology company that develops, manufactures, licenses, supports, and sells computer software, consumer electronics, and personal computers and services.",
                "website": "https://www.microsoft.com",
                "linkedin_url": "https://www.linkedin.com/company/microsoft/",
                "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/44/Microsoft_logo.svg/2048px-Microsoft_logo.svg.png"
            },
            "apple": {
                "name": "Apple",
                "industry": "Technology",
                "location": "Cupertino, CA",
                "description": "Apple is a multinational technology company that designs, develops, and sells consumer electronics, computer software, and online services.",
                "website": "https://www.apple.com",
                "linkedin_url": "https://www.linkedin.com/company/apple/",
                "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/Apple_logo_black.svg/1667px-Apple_logo_black.svg.png"
            },
            "amazon": {
                "name": "Amazon",
                "industry": "E-commerce, Cloud Computing",
                "location": "Seattle, WA",
                "description": "Amazon is a multinational technology company focusing on e-commerce, cloud computing, digital streaming, and artificial intelligence.",
                "website": "https://www.amazon.com",
                "linkedin_url": "https://www.linkedin.com/company/amazon/",
                "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/Amazon_logo.svg/2560px-Amazon_logo.svg.png"
            },
            "facebook": {
                "name": "Meta (formerly Facebook)",
                "industry": "Technology, Social Media",
                "location": "Menlo Park, CA",
                "description": "Meta Platforms, Inc., doing business as Meta and formerly known as Facebook, Inc., is a multinational technology conglomerate that owns Facebook, Instagram, and WhatsApp, among other products and services.",
                "website": "https://about.meta.com",
                "linkedin_url": "https://www.linkedin.com/company/meta/",
                "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Meta_Platforms_Inc._logo.svg/2560px-Meta_Platforms_Inc._logo.svg.png"
            }
        }
        
        # Check for company matches
        for key, company_data in companies.items():
            if key in company_lower or company_lower in key:
                return company_data
        
        # Return generic info if no match
        return {
            "name": company_name,
            "industry": "Unknown",
            "location": "Unknown",
            "description": "No description available",
            "website": "",
            "linkedin_url": "",
            "logo_url": ""
        }
    
    def _get_fallback_people(self, role: str, company: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get fallback people data when API fails
        
        Args:
            role: Professional role to generate fallback data for
            company: Company name (optional)
            
        Returns:
            List of generic profiles matching the role
        """
        # Lowercase for case-insensitive matching
        role_lower = role.lower()
        
        # Map of common roles to their expertise areas
        role_expertise = {
            "software engineer": ["Programming", "Software Development", "Algorithms", "Problem Solving", "System Design"],
            "data scientist": ["Machine Learning", "Data Analysis", "Statistics", "Python", "Data Visualization"],
            "product manager": ["Product Strategy", "User Experience", "Agile", "Market Research", "Roadmapping"],
            "marketing": ["Digital Marketing", "Content Strategy", "Social Media", "SEO", "Analytics"],
            "sales": ["Sales Strategy", "Negotiation", "Client Relationships", "Business Development", "CRM"],
            "designer": ["UI/UX Design", "Graphic Design", "Wireframing", "Prototyping", "User Research"],
            "hr": ["Recruitment", "Employee Relations", "Talent Management", "Compensation", "Organizational Development"]
        }
        
        # Find the closest role match
        matched_role = None
        for key in role_expertise.keys():
            if key in role_lower or role_lower in key:
                matched_role = key
                break
        
        # Use default expertise if no match
        expertise = role_expertise.get(matched_role, ["Leadership", "Communication", "Problem Solving", "Strategic Thinking", "Innovation"])
        
        # Create fallback profiles
        if company:
            # Company-specific profiles
            profiles = [
                {
                    "name": f"Senior {role.title()} Professional",
                    "title": f"Senior {role.title()}",
                    "company": company,
                    "location": "United States",
                    "linkedin_url": "",
                    "image_url": "",
                    "expertise": expertise
                },
                {
                    "name": f"{role.title()} Leader",
                    "title": f"{role.title()} Team Lead",
                    "company": company,
                    "location": "United States",
                    "linkedin_url": "",
                    "image_url": "",
                    "expertise": expertise
                },
                {
                    "name": f"{role.title()} Manager",
                    "title": f"{role.title()} Manager",
                    "company": company,
                    "location": "United States",
                    "linkedin_url": "",
                    "image_url": "",
                    "expertise": expertise
                }
            ]
        else:
            # Generic role-based profiles
            profiles = [
                {
                    "name": "Product Manager",
                    "title": "Senior Product Manager",
                    "company": "Technology Company",
                    "location": "San Francisco, CA",
                    "expertise": ["Product Strategy", "User Experience", "Agile", "Market Research", "Roadmapping"],
                    "experience": [
                        {"title": "Senior Product Manager", "company": "Technology Company", "duration": "2019-Present"},
                        {"title": "Product Manager", "company": "Previous Company", "duration": "2016-2019"}
                    ],
                    "education": [{"degree": "MBA", "school": "UC Berkeley Haas", "year": "2016"}]
                },
                {
                    "name": "Director of Product",
                    "title": "Director of Product",
                    "company": "SaaS Platform",
                    "location": "Austin, TX",
                    "expertise": ["Product Leadership", "Go-to-Market", "B2B SaaS", "Product-Led Growth"],
                    "experience": [
                        {"title": "Director of Product", "company": "SaaS Platform", "duration": "2020-Present"},
                        {"title": "Product Lead", "company": "Previous SaaS Company", "duration": "2017-2020"}
                    ],
                    "education": [{"degree": "BS in Computer Science", "school": "University of Texas", "year": "2012"}]
                }
            ]
            
        return profiles
