from flask import render_template, redirect, url_for, flash, request, jsonify, current_app, abort
from flask_login import login_required, current_user
from datetime import date, timedelta
import re # <-- Add import for regex
from decimal import Decimal, InvalidOperation # <-- Add imports for quantity handling
from flask_wtf.csrf import generate_csrf # Add CSRF token generation

from app import db
from app.models import Ingredient, Recipe, User, user_completed_recipes # Import User if needed for recipe saving checks
from . import fridge # Import the blueprint instance
from app.forms import IngredientForm, UpdateIngredientQuantityForm
from app.utils import fetch_product_info, get_recipe_suggestions # We will create utils.py later

@fridge.route('/', methods=['GET', 'POST'])
@login_required
def index():
    """Display user's ingredients and handle adding new ones."""
    form = IngredientForm()
    if form.validate_on_submit():
        try:
            expiry_dt = form.expiry_date.data
            ingredient = Ingredient(
                name=form.name.data,
                quantity=form.quantity.data,
                unit=form.unit.data,
                weight=form.weight.data,
                weight_unit=form.weight_unit.data,
                expiry_date=expiry_dt,
                owner=current_user
            )
            db.session.add(ingredient)
            db.session.commit()
            flash('Ingredient added successfully!', 'success')
            return redirect(url_for('fridge.index')) # Redirect to clear form
        except Exception as e:
            db.session.rollback()
            flash('Error adding ingredient. Please try again.', 'danger')
            current_app.logger.error(f"Error adding ingredient: {e}")
            
    # Fetch ingredients sorted by name or expiry date
    ingredients = current_user.ingredients.order_by(Ingredient.name).all()
    # You could also sort by expiry date, handling None values:
    # from sqlalchemy import nullsfirst
    # ingredients = current_user.ingredients.order_by(nullsfirst(Ingredient.expiry_date)).all()
    
    today = date.today()
    return render_template('fridge.html', title='My Fridge', form=form, 
                           ingredients=ingredients, today=today, timedelta=timedelta,
                           UpdateQtyForm=UpdateIngredientQuantityForm)

@fridge.route('/delete/<int:ingredient_id>', methods=['POST'])
@login_required
def delete_ingredient(ingredient_id):
    """Delete an ingredient."""
    ingredient = Ingredient.query.get_or_404(ingredient_id)
    if ingredient.owner != current_user:
        abort(403) # Forbidden
    try:
        db.session.delete(ingredient)
        db.session.commit()
        flash('Ingredient deleted.', 'info')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting ingredient.', 'danger')
        current_app.logger.error(f"Error deleting ingredient {ingredient_id}: {e}")
    return redirect(url_for('fridge.index'))

@fridge.route('/update_quantity/<int:ingredient_id>', methods=['POST'])
@login_required
def update_quantity(ingredient_id):
    """Update the quantity or weight of an ingredient."""
    ingredient = Ingredient.query.get_or_404(ingredient_id)
    if ingredient.owner != current_user:
        abort(403)
        
    form = UpdateIngredientQuantityForm(prefix=str(ingredient_id))
    
    # Validate based on request.form directly if not using template rendering
    if form.validate_on_submit():
        try:
            updated = False
            if form.quantity.data is not None:
                 # Allow setting quantity to 0
                ingredient.quantity = form.quantity.data
                # Optionally clear unit if quantity is 0 or None?
                updated = True
            if form.weight.data is not None:
                ingredient.weight = form.weight.data
                # Optionally clear weight_unit if weight is 0 or None?
                updated = True
            
            if updated:
                db.session.commit()
                flash(f'{ingredient.name} updated.', 'success')
            else:
                flash('No changes submitted.', 'info') # Should not happen due to form validation
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating {ingredient.name}.', 'danger')
            current_app.logger.error(f"Error updating ingredient {ingredient_id}: {e}")
    else:
        # Combine form errors into a single flash message
        error_msgs = []
        for field, errors in form.errors.items():
            error_msgs.extend(errors)
        flash('Update failed: ' + "; ".join(error_msgs), 'danger')
        
    return redirect(url_for('fridge.index'))

# --- Barcode Lookup --- #
@fridge.route('/lookup_barcode/<barcode>', methods=['GET'])
@login_required
def lookup_barcode(barcode):
    """Endpoint to lookup product info by barcode (calls external API via utils)."""
    # Basic barcode validation (e.g., length, digits only) can be added here
    if not barcode or not barcode.isdigit():
        return jsonify({'error': 'Invalid barcode format.'}), 400
        
    try:
        product_info = fetch_product_info(barcode)
        if product_info:
            return jsonify(product_info)
        else:
            return jsonify({'error': 'Product not found for this barcode.'}), 404
    except Exception as e:
        current_app.logger.error(f"Barcode lookup error for {barcode}: {e}")
        return jsonify({'error': 'Failed to lookup barcode information.'}), 500

# --- Recipe Suggestions (AJAX) --- #
@fridge.route('/suggest_recipes', methods=['GET']) # Keep GET for simplicity with fetch URL
@login_required
def suggest_recipes():
    """Generate recipe suggestions based on current ingredients (AJAX endpoint)."""
    
    # Check if the request is AJAX
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Optionally redirect non-AJAX requests or return an error/different page
        # For now, let's redirect back to the fridge page
        flash('This action requires JavaScript.', 'warning')
        return redirect(url_for('fridge.index'))
        
    try:
        servings = int(request.args.get('servings', 2))
        if servings <= 0:
            servings = 2
    except ValueError:
        servings = 2
        
    ingredients = current_user.ingredients.all()
    if not ingredients:
         return jsonify({'success': False, 'error': 'No ingredients in fridge.'}), 400

    # Format ingredient list for the API call
    ingredient_list = [
        f"{i.name}" + (f" ({i.quantity} {i.unit}" if i.quantity and i.unit else "") + (f" / {i.weight} {i.weight_unit}" if i.weight and i.weight_unit else "") + ")"
        for i in ingredients
    ]
    
    try:
        if not current_app.config.get('OPENROUTER_API_KEY'):
             return jsonify({'success': False, 'error': 'Recipe suggestion API is not configured.'}), 500
             
        # --- IMPORTANT: Ensure get_recipe_suggestions uses a STRICT prompt --- #
        # Modify the prompt within app.utils.get_recipe_suggestions to explicitly state: 
        # "ONLY use the ingredients provided in the list below. Do not add any other ingredients.
        #  Format the output clearly with sections for Title, Ingredients, and Instructions for each recipe."
        suggested_recipes_data = get_recipe_suggestions(ingredient_list, servings=servings)
        
        if suggested_recipes_data:
             # Return JSON for AJAX request
            return jsonify({
                'success': True,
                'recipes': suggested_recipes_data,
                'save_url': url_for('fridge.save_recipe'),
                'csrf_token': generate_csrf() # Generate fresh CSRF token for the save form
            })
        else:
             return jsonify({'success': False, 'error': 'Could not generate suggestions.'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Recipe suggestion error for user {current_user.id}: {e}")
        return jsonify({'success': False, 'error': f'An error occurred: {str(e)}'}), 500

# --- Saved Recipes --- #
@fridge.route('/recipes/save', methods=['POST'])
@login_required
def save_recipe():
    """Saves a recipe (likely from suggestions) to the database and user's list."""
    # Expecting recipe data (title, ingredients, instructions) in form post
    title = request.form.get('title')
    ingredients_text = request.form.get('ingredients')
    instructions = request.form.get('instructions')
    source = request.form.get('source', 'AI Generated') 
    
    if not title or not ingredients_text or not instructions:
        flash('Incomplete recipe data provided.', 'warning')
        # Redirect back to suggestions or fridge index?
        return redirect(request.referrer or url_for('fridge.index')) 

    try:
        # Optional: Check if an identical recipe already exists to avoid duplicates?
        existing_recipe = Recipe.query.filter_by(title=title, ingredients_text=ingredients_text).first()
        if existing_recipe:
            recipe = existing_recipe
        else:
            recipe = Recipe(
                title=title,
                ingredients_text=ingredients_text,
                instructions=instructions,
                source=source
            )
            db.session.add(recipe)
            # Need to commit here if it's a new recipe so it gets an ID
            db.session.flush() # Use flush to get ID without full commit yet
            
        # Add recipe to user's saved list
        if not current_user.has_saved_recipe(recipe):
            current_user.save_recipe(recipe)
            db.session.commit()
            flash(f'Recipe "{recipe.title}" saved!', 'success')
        else:
            db.session.rollback() # Rollback if we flushed but didn't need to save user link
            flash(f'Recipe "{recipe.title}" is already in your saved list.', 'info')

    except Exception as e:
        db.session.rollback()
        flash('Error saving recipe.', 'danger')
        current_app.logger.error(f"Error saving recipe '{title}': {e}")
        
    # Redirect to saved recipes list or fridge index
    return redirect(url_for('fridge.saved_recipes'))

@fridge.route('/recipes/saved', methods=['GET'])
@login_required
def saved_recipes():
    """Display the user's saved recipes."""
    recipes = current_user.saved_recipes.order_by(Recipe.title).all()
    return render_template('saved_recipes.html', title='Saved Recipes', recipes=recipes)

@fridge.route('/recipe/<int:recipe_id>')
@login_required
def view_recipe(recipe_id):
    """Display the details of a specific saved recipe."""
    recipe = Recipe.query.get_or_404(recipe_id)
    # Ensure the user has saved this recipe to view it?
    # Or allow viewing any recipe by ID if desired
    if not current_user.has_saved_recipe(recipe):
         # If we only allow viewing saved recipes:
         # flash('Recipe not found in your saved list.', 'warning')
         # return redirect(url_for('fridge.saved_recipes'))
         # If we allow viewing any recipe, just pass a flag:
         is_saved = False
    else:
        is_saved = True
        
    return render_template('view_recipe.html', title=recipe.title, recipe=recipe, is_saved=is_saved)

@fridge.route('/recipe/delete/<int:recipe_id>', methods=['POST'])
@login_required
def delete_saved_recipe(recipe_id):
    """Remove a recipe from the user's saved list (doesn't delete the Recipe object itself)."""
    recipe = Recipe.query.get_or_404(recipe_id)
    if current_user.has_saved_recipe(recipe):
        try:
            current_user.unsave_recipe(recipe)
            db.session.commit()
            flash(f'Recipe "{recipe.title}" removed from your saved list.', 'info')
        except Exception as e:
            db.session.rollback()
            flash('Error removing saved recipe.', 'danger')
            current_app.logger.error(f"Error unsaving recipe {recipe_id} for user {current_user.id}: {e}")
    else:
        flash('Recipe not found in your saved list.', 'warning')
        
    return redirect(url_for('fridge.saved_recipes'))

# --- Completed Recipes Page --- #
@fridge.route('/recipes/completed', methods=['GET'])
@login_required
def completed_recipes():
    """Display the user's completed recipes."""
    # Query using the relationship, order by completion time descending
    recipes = current_user.completed_recipes.join(user_completed_recipes).order_by(
        user_completed_recipes.c.completed_at.desc()
    ).all()
    
    # We might need completion dates in the template, so fetch them too
    completion_dates = {row.recipe_id: row.completed_at 
                        for row in db.session.query(user_completed_recipes).filter_by(user_id=current_user.id).all()}
    
    return render_template('completed_recipes.html', title='Completed Recipes', 
                           recipes=recipes, completion_dates=completion_dates)

def parse_recipe_ingredient(line):
    """Rudimentary parsing of a recipe ingredient line.
       Attempts to extract quantity, unit, and name.
       Example: "2 cups Flour" -> (Decimal('2'), 'cups', 'Flour')
                "1 Egg" -> (Decimal('1'), None, 'Egg')
                "Salt" -> (None, None, 'Salt')
       Returns: (quantity, unit, name) or None if parsing fails
    """
    line = line.strip()
    if not line: 
        return None

    # Regex to find initial number (int or float) and optional unit
    # Allows for formats like "1", "1.5", "1/2", "1 1/2"
    # (\d+(\.\d+)?|\d+/\d+|\d+\s+\d+/\d+) -> number part
    # (\s+)?(\w+) -> optional space and unit
    # (.*) -> the rest is the name
    match = re.match(r"^(\d+(?:\.\d+)?|\d+/\d+|\d+\s+\d+/\d+)?\s*([\w-]+(?:\s+[\w-]+)?)?\s+(.*)$", line)
    
    qty = None
    unit = None
    name = line # Default name is the whole line if no qty/unit found
    
    if match:
        qty_str, unit_str, name_str = match.groups()
        
        # Parse quantity
        if qty_str:
            try:
                # Handle fractions like "1/2" or mixed like "1 1/2"
                if '/' in qty_str:
                    if ' ' in qty_str: # Mixed fraction "1 1/2"
                        parts = qty_str.split()
                        qty = Decimal(parts[0]) + Decimal(parts[1].split('/')[0]) / Decimal(parts[1].split('/')[1])
                    else: # Simple fraction "1/2"
                        parts = qty_str.split('/')
                        qty = Decimal(parts[0]) / Decimal(parts[1])
                else:
                    qty = Decimal(qty_str)
            except (InvalidOperation, ValueError, ZeroDivisionError):
                current_app.logger.warning(f"Could not parse quantity '{qty_str}' in recipe line: {line}")
                qty = None # Failed to parse quantity
       
        unit = unit_str.strip() if unit_str else None
        name = name_str.strip()
       
    elif re.match(r"^([\w-]+(?:\s+[\w-]+)?)\s+(.*)$", line):
         # Check for format "Unit Name" (no initial quantity)
        match_unit_name = re.match(r"^([\w-]+(?:\s+[\w-]+)?)\s+(.*)$", line)
        if match_unit_name:
             unit, name = match_unit_name.groups()
             unit = unit.strip()
             name = name.strip()
    
    # Clean up common unit variations (very basic)
    if unit:
        unit_lower = unit.lower()
        if unit_lower in ['g', 'gram', 'grams']:
            unit = 'g'
        elif unit_lower in ['kg', 'kilogram', 'kilograms']:
             unit = 'kg'
        elif unit_lower in ['ml', 'milliliter', 'milliliters']:
            unit = 'ml'
        elif unit_lower in ['l', 'liter', 'liters']:
            unit = 'l'
        # Add more conversions as needed (cups, oz, tbsp, etc.)
        # This is where it gets complex!

    return qty, unit, name.lower() # Return name in lowercase for matching

@fridge.route('/recipe/use/<int:recipe_id>', methods=['POST'])
@login_required
def use_recipe(recipe_id):
    """Decrements used ingredients from the fridge after parsing recipe text."""
    recipe = Recipe.query.get_or_404(recipe_id)
    # Ensure user has saved the recipe (or remove this check if not desired)
    # if not current_user.has_saved_recipe(recipe):
    #     flash('Cannot use a recipe not in your saved list.', 'warning')
    #     return redirect(url_for('fridge.saved_recipes'))

    required_items = []
    parsing_errors = []
    
    # 1. Parse recipe ingredients_text
    for line in recipe.ingredients_text.strip().split('\n'):
        parsed = parse_recipe_ingredient(line)
        if parsed:
            qty, unit, name = parsed
            if name: # Must have at least a name
                required_items.append({'name': name, 'qty': qty, 'unit': unit, 'original_line': line})
            else:
                 parsing_errors.append(line)
        elif line.strip(): # Only report non-empty lines as errors
            parsing_errors.append(line)
           
    if parsing_errors:
        flash(f"Could not fully understand recipe ingredients: {'; '.join(parsing_errors)}. Deduction skipped.", 'warning')
        current_app.logger.warning(f"Parsing errors for recipe {recipe_id}: {parsing_errors}")
        return redirect(url_for('fridge.view_recipe', recipe_id=recipe.id))
       
    if not required_items:
         flash(f"No ingredients found in recipe '{recipe.title}'. Deduction skipped.", 'warning')
         return redirect(url_for('fridge.view_recipe', recipe_id=recipe.id))

    # 2. Check availability and prepare deductions
    fridge_ingredients = {ing.name.lower(): ing for ing in current_user.ingredients.all()}
    deductions = []
    missing_ingredients = []
    unit_mismatches = []

    for item in required_items:
        req_name = item['name']
        req_qty = item['qty']
        req_unit = item['unit']
        
        fridge_match = fridge_ingredients.get(req_name)

        if not fridge_match:
            missing_ingredients.append(item['original_line'])
            continue

        # --- START: Refined Quantity/Weight Checking & Deduction Logic --- #
        can_deduct = False
        deduction_amount = req_qty
        deduct_from = None # 'quantity' or 'weight'

        if req_qty is not None: # Recipe specifies a quantity
            # Priority 1: Try matching quantity field + unit
            if fridge_match.quantity is not None:
                # Allow if units match OR if recipe unit is None OR if fridge unit is None
                if req_unit is None or not fridge_match.unit or req_unit.lower() == fridge_match.unit.lower():
                    if fridge_match.quantity >= float(req_qty): # Convert Decimal to float for comparison
                        can_deduct = True
                        deduct_from = 'quantity'
                # Else: Units explicitly mismatch for the quantity field, don't use it

            # Priority 2: If quantity didn't work/match, try matching weight field + unit
            if not can_deduct and fridge_match.weight is not None:
                # Allow if units match OR if recipe unit is None OR if fridge unit is None (for weight)
                if req_unit is None or not fridge_match.weight_unit or req_unit.lower() == fridge_match.weight_unit.lower():
                    if fridge_match.weight >= float(req_qty): # Convert Decimal to float for comparison
                        can_deduct = True
                        deduct_from = 'weight'
                # Else: Units explicitly mismatch for the weight field, don't use it
            
            # If still cannot deduct after checking both quantity and weight
            if not can_deduct:
                # Construct appropriate error message based on checks
                fridge_qty_str = f"{fridge_match.quantity or 'N/A'} {fridge_match.unit or ''}".strip()
                fridge_wt_str = f"{fridge_match.weight or 'N/A'} {fridge_match.weight_unit or ''}".strip()
                needed_str = f"{req_qty} {req_unit or ''}".strip()
                
                # Check if there was an explicit unit mismatch found that prevented deduction
                unit_mismatch = False
                if fridge_match.quantity is not None and req_unit is not None and fridge_match.unit and req_unit.lower() != fridge_match.unit.lower():
                     unit_mismatch = True # Mismatch on quantity field
                if not unit_mismatch and fridge_match.weight is not None and req_unit is not None and fridge_match.weight_unit and req_unit.lower() != fridge_match.weight_unit.lower():
                     unit_mismatch = True # Mismatch on weight field

                if unit_mismatch:
                    unit_mismatches.append(f"{item['original_line']} (Fridge Qty:'{fridge_qty_str}', Wt:'{fridge_wt_str}' / Recipe needs:'{needed_str}' - Unit mismatch)")

        if can_deduct and deduction_amount is not None:
            deductions.append({
                'ingredient_obj': fridge_match,
                'deduct_amount': deduction_amount,
                'deduct_from': deduct_from # 'quantity' or 'weight'
            })
        elif not can_deduct and req_qty is not None: # If deduction failed and qty was specified
             # Error already added to missing or mismatch lists
             pass
            
    # 3. Perform deductions if all checks passed
    if not missing_ingredients and not unit_mismatches:
        try:
            deleted_items = []
            updated_items = []
            for ded in deductions:
                ing = ded['ingredient_obj']
                amount = ded['deduct_amount']
                field = ded['deduct_from']
                
                if field == 'quantity':
                    ing.quantity -= float(amount) # Use float for DB compatibility
                    if ing.quantity <= 0:
                         deleted_items.append(ing.name)
                         db.session.delete(ing)
                    else:
                         updated_items.append(f"{ing.name} (New Qty: {ing.quantity})")
                         db.session.add(ing)
                elif field == 'weight':
                     ing.weight -= float(amount)
                     if ing.weight <= 0:
                         deleted_items.append(ing.name)
                         db.session.delete(ing)
                     else:
                         updated_items.append(f"{ing.name} (New Wt: {ing.weight})")
                         db.session.add(ing)
                        
            # --- NEW: Mark recipe as completed and unsave --- #
            current_user.unsave_recipe(recipe) # Remove from saved list
            current_user.complete_recipe(recipe) # Add to completed list
            # --- End New --- #
                        
            db.session.commit()
            flash(f'Successfully used recipe "{recipe.title}"! Ingredients deducted.', 'success')
            if updated_items:
                 flash(f"Updated: {'; '.join(updated_items)}", 'info')
            if deleted_items:
                flash(f"Removed due to depletion: {', '.join(deleted_items)}", 'info')
            # --- UPDATED REDIRECT --- #
            return redirect(url_for('fridge.completed_recipes')) 
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred during ingredient deduction: {e}', 'danger')
            current_app.logger.error(f"Error deducting ingredients for recipe {recipe_id}: {e}")
            return redirect(url_for('fridge.view_recipe', recipe_id=recipe.id))
    else:
        # Report errors
        error_msg = "Cannot use recipe. "
        if missing_ingredients:
             error_msg += "Missing or insufficient ingredients: " + "; ".join(missing_ingredients) + ". "
        if unit_mismatches:
             error_msg += "Unit mismatches (cannot convert): " + "; ".join(unit_mismatches) + ". Please update fridge items or recipe." 
        flash(error_msg, 'danger')
        return redirect(url_for('fridge.view_recipe', recipe_id=recipe.id)) 
