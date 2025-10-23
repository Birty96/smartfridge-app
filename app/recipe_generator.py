"""
Recipe Generation and Parsing Classes

This module contains classes for generating recipes from AI APIs and parsing
the responses into structured data.
"""

import re
import json
from typing import List, Dict, Optional, Tuple, Any
from flask import current_app
from openai import OpenAI
import httpx


class RecipeParser:
    """
    Handles parsing of AI-generated recipe responses into structured data.
    """
    
    def __init__(self):
        self.logger = current_app.logger if current_app else None
    
    def parse_markdown_recipes(self, raw_response: str) -> List[Dict[str, Any]]:
        """
        Parse markdown-formatted recipes from AI response.
        
        Expected format:
        ## Recipe Title
        ### Ingredients
        * ingredient 1
        * ingredient 2
        ### Instructions
        1. Step 1
        2. Step 2
        
        Args:
            raw_response: The raw markdown response from AI
            
        Returns:
            List of dictionaries with keys: title, ingredients, instructions
        """
        if self.logger:
            self.logger.debug(f"Parsing recipe response: {raw_response[:200]}...")
        
        recipes = []
        current_recipe = None
        current_section = None
        
        for line in raw_response.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # New recipe title detection
            if line.startswith('## '):
                if current_recipe:
                    validated_recipe = self._validate_recipe(current_recipe)
                    if validated_recipe:
                        recipes.append(validated_recipe)
                    else:
                        self._log_warning(f"Discarding invalid recipe: {current_recipe.get('title')}")
                
                current_recipe = {
                    'title': line[3:].strip(),
                    'ingredients': [],
                    'instructions': []
                }
                current_section = None
                continue
            
            # Section header detection
            if current_recipe:
                if line.lower().startswith('### ingredients'):
                    current_section = 'ingredients'
                    continue
                elif line.lower().startswith('### instructions'):
                    current_section = 'instructions'
                    continue
                
                # Parse content based on current section
                if current_section == 'ingredients':
                    ingredient = self._parse_ingredient_line(line)
                    if ingredient:
                        current_recipe['ingredients'].append(ingredient)
                elif current_section == 'instructions':
                    instruction = self._parse_instruction_line(line)
                    if instruction:
                        current_recipe['instructions'].append(instruction)
        
        # Add the last recipe if valid
        if current_recipe:
            validated_recipe = self._validate_recipe(current_recipe)
            if validated_recipe:
                recipes.append(validated_recipe)
            else:
                self._log_warning(f"Discarding invalid last recipe: {current_recipe.get('title')}")
        
        return recipes
    
    def _parse_ingredient_line(self, line: str) -> Optional[str]:
        """Parse a single ingredient line."""
        if line.startswith('* ') or line.startswith('- '):
            return line[2:].strip()
        elif len(line) > 1:
            return line
        return None
    
    def _parse_instruction_line(self, line: str) -> Optional[str]:
        """Parse a single instruction line."""
        if line.startswith('* ') or line.startswith('- '):
            return line[2:].strip()
        elif line[:1].isdigit() and (line[1:3] == '. ' or line[1:2] == '.'):
            return line.split('.', 1)[-1].strip()
        elif len(line) > 1:
            return line
        return None
    
    def _validate_recipe(self, recipe: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate that a recipe has all required components."""
        if not recipe.get('title'):
            return None
        if not recipe.get('ingredients') or len(recipe['ingredients']) == 0:
            return None
        if not recipe.get('instructions') or len(recipe['instructions']) == 0:
            return None
        return recipe
    
    def _log_warning(self, message: str):
        """Log a warning message if logger is available."""
        if self.logger:
            self.logger.warning(message)


class RecipeGenerator:
    """
    Handles communication with AI APIs to generate recipes.
    """
    
    # Constants for the class
    MAX_TOKENS = 1024
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MODEL = "mistralai/mistral-7b-instruct:free"
    BASE_URL = "https://openrouter.ai/api/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._get_api_key()
        self.parser = RecipeParser()
        self.logger = current_app.logger if current_app else None
    
    def _get_api_key(self) -> str:
        """Get API key from Flask config."""
        if not current_app:
            raise ValueError("Flask application context required")
        
        api_key = current_app.config.get('OPENROUTER_API_KEY')
        if not api_key:
            raise ValueError("Recipe suggestion API key is not configured.")
        return api_key
    
    def generate_recipes(self, ingredient_list: List[str], servings: int = 2) -> Optional[List[Dict[str, Any]]]:
        """
        Generate recipes based on available ingredients.
        
        Args:
            ingredient_list: List of available ingredients
            servings: Number of servings to target
            
        Returns:
            List of recipe dictionaries or None if generation fails
        """
        try:
            response = self._call_ai_api(ingredient_list, servings)
            recipes = self.parser.parse_markdown_recipes(response)
            
            if not recipes:
                self._log_warning("Failed to parse any recipes from AI response.")
                return None
            
            return recipes[:3]  # Return up to 3 recipes
            
        except Exception as e:
            self._log_error(f"Error generating recipes: {e}")
            raise
    
    def _call_ai_api(self, ingredient_list: List[str], servings: int) -> str:
        """Make the actual API call to the AI service."""
        http_client = httpx.Client()
        
        client = OpenAI(
            base_url=self.BASE_URL,
            api_key=self.api_key,
            http_client=http_client
        )
        
        prompt = self._build_prompt(ingredient_list, servings)
        system_message = self._build_system_message()
        
        completion = client.chat.completions.create(
            model=self.DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            max_tokens=self.MAX_TOKENS,
            temperature=self.DEFAULT_TEMPERATURE,
        )
        
        response = completion.choices[0].message.content
        
        if self.logger:
            self.logger.debug(f"Raw AI response: {response[:200]}...")
        
        return response
    
    def _build_prompt(self, ingredient_list: List[str], servings: int) -> str:
        """Build the prompt for the AI."""
        ingredients_str = '\n'.join(ingredient_list)
        
        return (
            f"You are a recipe generator. Your task is to generate up to 3 recipes based *ONLY* on the provided ingredients list and serving size.\n\n"
            f"**CRITICAL CONSTRAINTS:**\n"
            f"1. **INGREDIENT LIST IS EXHAUSTIVE:** You ABSOLUTELY MUST NOT use any ingredients, spices, oils, liquids (even water), or pantry staples NOT explicitly listed in 'Available Ingredients'. If a common recipe needs an unlisted item, DO NOT suggest that recipe. Suggest something else that uses *only* the provided items.\n"
            f"2. **SERVINGS:** Target recipes suitable for {servings} servings. Estimate ingredient amounts appropriately.\n"
            f"3. **OUTPUT FORMAT (Strict Markdown):**\n"
            f"   * Start EACH recipe's title with exactly `## ` (e.g., `## Simple Omelette`).\n"
            f"   * Follow the title immediately with the ingredients list, starting exactly with `### Ingredients`. Use markdown bullets (`*` or `-`) for each ingredient.\n"
            f"   * Follow the ingredients immediately with the instructions, starting exactly with `### Instructions`. Use a numbered markdown list (`1.`, `2.`) for steps.\n\n"
            f"**Available Ingredients:**\n{ingredients_str}\n\n"
            f"**REMINDER:** Do NOT use any ingredient not on the list above."
        )
    
    def _build_system_message(self) -> str:
        """Build the system message for the AI."""
        return (
            "You are a recipe assistant that strictly follows user constraints. "
            "You ONLY use ingredients listed in the user prompt's 'Available Ingredients' section. "
            "You format EACH recipe precisely using Markdown: Title starts with '## ', ingredients section with '### Ingredients' and bullets (* or -), instructions section with '### Instructions' and numbers (1., 2.)."
        )
    
    def _log_warning(self, message: str):
        """Log a warning message if logger is available."""
        if self.logger:
            self.logger.warning(message)
    
    def _log_error(self, message: str):
        """Log an error message if logger is available."""
        if self.logger:
            self.logger.error(message)


# Convenience function to maintain backward compatibility
def get_recipe_suggestions(ingredient_list: List[str], servings: int = 2) -> Optional[List[Dict[str, Any]]]:
    """
    Legacy function for generating recipe suggestions.
    
    This function maintains backward compatibility with existing code
    while using the new RecipeGenerator class internally.
    """
    generator = RecipeGenerator()
    return generator.generate_recipes(ingredient_list, servings)