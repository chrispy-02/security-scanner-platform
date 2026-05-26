from flask import current_app as app
from flask import render_template, redirect, session, url_for, request, \
    jsonify, flash, send_file, g
# from flask_restful import Api, Resource
import secrets
import json
import functools
import os
import sys
import zipfile
from authlib.integrations.flask_client import OAuth
import glob
import os.path
import ast
import math as mth
import time

current_dir = os.path.dirname(os.path.abspath(__file__))

# get path to scan_parse.py
sys.path.insert(0, current_dir)

from scan_parse import process_report
from utility import run_scan, refresh_scan_status, cancel_scan_run

db = app.db
scheduler = app.scheduler

CLIENT_ID = os.getenv("OAUTH_ID")
CLIENT_SECRET = os.getenv("OAUTH_SECRET")

oauth = OAuth(app)
google = oauth.register(

    name='google',
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid profile email'}
)


#######################################################################################
# AUTHENTICATION RELATED
#######################################################################################

# Forces routes to login page if no email in session
def login_required(func):
    @functools.wraps(func)
    def secure_function(*args, **kwargs):
        if "email" not in session:
            return redirect(url_for("login", next_page=request.url))
        return func(*args, **kwargs)

    return secure_function


def api_key_required(func):
    @functools.wraps(func)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('API-Key')
        # check for api key
        if not api_key:
            return jsonify({'message': 'API key is missing!'}), 401

        data = request.get_json()
        if not data or 'email' not in data:
            return jsonify({'message' : 'Email is missing from the json body!'}), 400
        
        user_email = data.get('email')
        target_email, user_id = db.api_authenticate(api_key)
        # checks that the user's email and api key match
        if ((target_email == -1) or (target_email != user_email)):
            return jsonify({'message': 'Invalid API key or email!'}), 401
        # stores the user_id within the current flask request context
        g.current_user_id = user_id

        return func(*args, **kwargs)

    return decorated


# Get user email from session
def getUser():
    return db.reversibleEncrypt('decrypt', session['email']) if 'email' in session else 'Unknown'

# Get user role from db
def getRole():
    try:
        result = db.query(f"SELECT role FROM users WHERE email = '{str(getUser())}'")[0]['role']
    except IndexError:
        return 'unknown'

    return result

# displays the dashboard for the user
@app.route('/api/dashboard', methods=['POST'])
@api_key_required
def dashboard_api():
    # gets user_id from the context
    user_id = g.current_user_id
    sites = get_dashboard_sites(user_id)
    if not sites:
        return jsonify({'message': 'No websites found'}), 200
    website_indexed_dict = {}
    # improves readability by having website names in objects
    for site in sites:
        site_name = site.pop('website_name')
        website_indexed_dict[site_name] = site
    return jsonify(website_indexed_dict), 200

# displays website group
@app.route('/api/website/<website_id>', methods=['POST'])
@api_key_required
def website_api(website_id):
    # owner and admin can access all websites
    priv_users = ['owner', 'admin']
    # gets user_id from current context
    user_id = g.current_user_id
    website_auth_query = "SELECT * FROM website_auth WHERE website_id = %s AND user_id = %s"
    auth_result = db.query(website_auth_query, [website_id, user_id])
    role_query = "SELECT role FROM users WHERE user_id = %s"
    role = db.query(role_query, [user_id])[0]['role']
    # checks to see if the user has acess to site or they are an owner or admin role
    if ((auth_result == []) and (role not in priv_users)):
        return jsonify({'message': "You don't have access to view this website"}), 401
    scans = get_website_scans(website_id)
    scans_indexed_dict = {}
    # improves readability by having scan ids in objects
    for scan in scans:
        scan_id = scan.pop('scan_id')
        scans_indexed_dict[scan_id] = scan
    if scans == []:
        return jsonify({'message': 'No websites found'}), 200
    return jsonify(scans_indexed_dict), 200

# runs quick scan for website group
@app.route('/api/website/<website_id>/quick-scan', methods=['POST'])
@api_key_required
def quick_scan_api(website_id):
    # owner and admin can access all websites
    priv_users = ['owner', 'admin']
    user_id = g.current_user_id
    website_auth_query = "SELECT * FROM website_auth WHERE website_id = %s AND user_id = %s"
    auth_result = db.query(website_auth_query, [website_id, user_id])
    role_query = "SELECT role FROM users WHERE user_id = %s"
    role = db.query(role_query, [user_id])[0]['role']
    # checks to see if the user has access to site or they are an owner or admin role
    if ((auth_result == []) and (role not in priv_users)):
        return jsonify({'message': "You don't have access to scan this website"}), 401
    website_info_query = "SELECT * FROM websites where website_id = %s"
    website_info = db.query(website_info_query, [website_id])[0]
    return run_scan(website_info['website_name'], website_info['website_url'], website_id, db, user_id)

# deletes website group
@app.route('/api/website/<website_id>/delete-website', methods=['POST'])
@api_key_required
def api_delete_website(website_id):
    # owner and admin can access all websites
    priv_users = ['owner', 'admin']
    user_id = g.current_user_id
    role_query = "SELECT role FROM users WHERE user_id = %s"
    role = db.query(role_query, [user_id])[0]['role']
    # checks to see if the user can delete the site by being owner or admin
    if (role not in priv_users):
        return jsonify({'message': "You don't have access to view this website"}), 401
    deleteWebsite(website_id)
    return jsonify({'message': f"Website {website_id} deleted"}), 401

# adds user to WEBSITE group
@app.route('/api/website/<website_id>/add-user', methods=['POST'])
@api_key_required
def api_add_user(website_id):
    data = request.get_json()
    if not data or 'added_user_email' not in data:
        return jsonify({'message' : 'Json data incorrect!'}), 400
    added_user_email = data.get('added_user_email')
    user_id = g.current_user_id
    role_query = "SELECT role FROM users WHERE user_id = %s"
    role = db.query(role_query, [user_id])[0]['role']
    # only admin can change who can access site
    if (role != "admin"):
        return jsonify({'message': "You don't have permission to add users"}), 401
    message = add_user(added_user_email, website_id)
    return jsonify({'message': message}), 200

# removes user from WEBSITE group
@app.route('/api/website/<website_id>/remove-user', methods=['POST'])
@api_key_required
def api_remove_user(website_id):
    data = request.get_json()
    if not data or 'removed_user_email' not in data:
        return jsonify({'message' : 'Json data incorrect!'}), 400
    removed_user_email = data.get('removed_user_email')
    user_id = g.current_user_id
    role_query = "SELECT role FROM users WHERE user_id = %s"
    role = db.query(role_query, [user_id])[0]['role']
    removed_user_id_query = "SELECT * FROM users WHERE email = %s"
    removed_user_id = db.query(removed_user_id_query, [removed_user_email])[0]
    # only admin can change who can access site
    if (role != "admin"):
        return jsonify({'message': "You don't have permission to remove users"}), 401
    message = delete_user(removed_user_id, website_id)
    return jsonify({'message': message}), 200

# shows users in a website group if admin or owner, but not other admins
@app.route('/api/website/<website_id>/show-users', methods=['POST'])
@api_key_required
def api_show_website_users(website_id):
    user_id = g.current_user_id
    role_query = "SELECT role FROM users WHERE user_id = %s"
    role = db.query(role_query, [user_id])[0]['role']
    # only admin can change who can access site
    if (role != "admin"):
        return jsonify({'message': "You don't have permission to view users"}), 401
    added_users_query = "SELECT * FROM website_auth WHERE website_id = %s"
    added_users = db.query(added_users_query, [website_id])
    added_users_dict = {}
    # makes the json more readable
    for user in added_users:
        user_email_query = "SELECT * FROM users where user_id = %s"
        user_email = db.query(user_email_query, [user['user_id']])[0]['email']
        added_users_dict[user['user_id']] = user_email
    return jsonify(added_users_dict), 200

# deletes scan from db with API call
@app.route('/api/website/<website_id>/delete-scan/<scan_id>', methods=['POST'])
@api_key_required
def api_delete_scan(website_id, scan_id):
    priv_users = ['owner', 'admin']
    user_id = g.current_user_id
    role_query = "SELECT role FROM users WHERE user_id = %s"
    role = db.query(role_query, [user_id])[0]['role']
    user_auth_query = "SELECT * FROM website_auth WHERE website_id = %s AND user_id = %s"
    user_auth = db.query(user_auth_query, [website_id, user_id])
    # only admin or owner can delete scans or if employee has website auth
    if ((role not in priv_users) and ((role != 'employee') or (user_auth == []))):
        return jsonify({'message': "You don't have permission to delete this scan!"}), 401
    return (deleteScan(scan_id)), 200

# register website group
@app.route('/api/website/register', methods=['POST'])
@api_key_required
def api_register_website():
    data = request.get_json()
    if not data or (('website_name' not in data) or ('website_url' not in data)) :
        return jsonify({'message' : 'Json data incorrect!'}), 400
    website_name = data.get('website_name')
    website_url = data.get('website_url')
    user_id = g.current_user_id
    return(register_website(user_id, website_name, website_url))

# show users available to user
@app.route('/api/settings/show-users', methods=['POST'])
@api_key_required
def api_show_users():
    user_id = g.current_user_id
    role_query = "SELECT role FROM users WHERE user_id = %s"
    role = db.query(role_query, [user_id])[0]['role']
    users = {}
    users_json = {}
    # owner is allowed to see all users
    if (role == 'owner'):
        users_query = "SELECT user_id, email, role FROM users"
        users = db.query(users_query)
    # admins can't see other admins
    if (role == 'admin'):
        users_query = "SELECT user_id, email, role FROM users WHERE role = %s OR role = %s OR user_id = %s"
        users = db.query(users_query, ['reader', 'employee', user_id])
    if users != {}:
        for user in users:
            users_json[user['user_id']] = [user['email'], user['role']]
        return jsonify(users_json), 200
    return jsonify({'message': "You don't have permission to acess users"}), 401

# changes user's role
@app.route('/api/settings/edit-roles', methods=['POST'])
@api_key_required
def api_edit_roles():
    data = request.get_json()
    if not data or (('edited_id' not in data) or ('new_role' not in data)) :
        return jsonify({'message' : 'Json data incorrect!'}), 400
    edited_id = data.get('edited_id')
    new_role = data.get('new_role')
    roles = ['owner', 'admin', 'employee', 'reader']
    if new_role not in roles:
        return(jsonify({'message': "That role does not exist"})), 400
    editor_id = g.current_user_id
    editor_role_query = "SELECT role FROM users WHERE user_id = %s"
    editor_role = db.query(editor_role_query, [editor_id])[0]['role']
    edited_user_curr_role_query = "SELECT * FROM users WHERE user_id = %s"
    edited_user_curr_role = db.query(edited_user_curr_role_query, [edited_id])[0]['role']
    # checks to make sure user exists
    if edited_user_curr_role == []:
        return jsonify({'message': "This user doesn't exist"})
    # checks to see if user can edit the role they are requesting to
    if (editor_role == 'owner'):
        if (new_role == edited_user_curr_role):
            return {'message': f"This user already has the role of {edited_user_curr_role}"}
        if (new_role == 'owner'):
            return({'message' : f"You can't give the role of {new_role}"}), 401
        if (edited_user_curr_role != 'owner'):
            update_query = "UPDATE users SET role = %s WHERE user_id = %s"
            db.query(update_query, [new_role, edited_id])
            return jsonify({'message': f"User {edited_id} has been updated to {new_role}"}), 200
        return jsonify({'message' : "The role of owner can not be changed"}), 401
    if (editor_role == 'admin'):
        if (new_role == edited_user_curr_role):
            return {'message': f"This user already has the role of {edited_user_curr_role}"}
        if ((edited_user_curr_role == 'owner') or (edited_user_curr_role == 'admin')):
            return jsonify({'message' : "You don't have permission to edit this user's role"}), 401
        if ((new_role == 'admin') or (new_role == 'owner')):
            return({'message' : f"You can't give the role of {new_role}"}), 401
        update_query = "UPDATE users SET role = %s WHERE user_id = %s"
        db.query(update_query, [new_role, edited_id])
        return jsonify({'message': f"User {edited_id} has been updated to {new_role}"}), 200
    return jsonify({'message': "You do not have permission to edit user roles"}), 401
    
# delete
@app.route('/api/settings/delete-user', methods=['POST'])
@api_key_required
def api_delete_users():
    data = request.get_json()
    if not data or ('deleted_id' not in data) :
        return jsonify({'message' : 'Json data incorrect!'}), 400
    deleted_id = data.get('deleted_id')
    user_id = g.current_user_id 
    deleting_user_curr_role_query = "SELECT * FROM users WHERE user_id = %s"
    deleting_user_curr_role = db.query(deleting_user_curr_role_query, [user_id])[0]['role']
    deleted_user_curr_role_query = "SELECT * FROM users WHERE user_id = %s"
    deleted_user_curr_info = db.query(deleted_user_curr_role_query, [deleted_id])
    deleted_user_curr_role = deleted_user_curr_info[0]['role']
    deleted_user_curr_email = deleted_user_curr_info[0]['email']
    if deleted_user_curr_role == []:
        return jsonify({'message': "This user doesn't exist"})
    # checks access level to see if the user is allowed to be deleted
    if (deleting_user_curr_role == 'owner'):
        if (deleted_user_curr_role != 'owner'):
            message, status = delete_user_sitewide(deleted_id, deleted_user_curr_email)
            return jsonify({'message': message}), 200
        return jsonify({'message' : "The owner can't be deleted"}), 401
    if (deleting_user_curr_role == 'admin'):
        if ((deleted_user_curr_role == 'owner') or (deleted_user_curr_role == 'admin')):
            return jsonify({'message' : "You don't have permission to edit this user's role"}), 401
        message, status = delete_user_sitewide(deleted_id, deleted_user_curr_email)
        return jsonify({'message': message}), 200
    return jsonify({'message': "You do not have permission to edit user roles"}), 401

# adds a new schedule to a site
@app.route('/api/website/<int:website_id>/schedule-scan/new-schedule', methods=['POST'])
@api_key_required
def api_add_schedule(website_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data"}), 400
    # always going to have this data
    try:
        time_interval = data.get("time_interval")
        scan_url = data.get("website_url")
        description = data.get("description")
    except:
        return jsonify({"message": f"Error Retrieving Schedule Data: {str(e)}"})
    # checks the type of scan
    if time_interval == "hourly":
        # unpackage data depending on data
        try:
            frequency, start_time, end_time, days_to_run = data.get("frequency"), data.get("start_time"), data.get("end_time"), data.get("days_to_run")
        except Exception as e:
            return jsonify({"message": f"Error Retrieving Schedule Data: {str(e)}"})
        # captalize days so that it is compatiable with datetime format in scheduler
        days_capitalized = capitalizeDays(days_to_run)
        # gets the proper run times for hourly scans
        run_times = hourly_scan(frequency, start_time, end_time)
        # passes data for scheduler
        scheduler.add_hourly_scan(frequency, days_capitalized, run_times, description, website_id, scan_url)

    if (time_interval == "daily") or (time_interval == "weekly") :
        try:
            specific_time, days_to_run = data.get("specific_time"), data.get("days_to_run")
        except Exception as e:
            return jsonify({"message": f"Error Retrieving Schedule Data: {str(e)}"})
        days_capitalized = capitalizeDays(days_to_run)
        scheduler.add_daily_or_weekly_scan(days_capitalized, specific_time, description, website_id, scan_url, time_interval)

    if time_interval == "monthly":
        try:
            specific_time, date_selected = data.get("specific_time"), data.get("date_selected")
        except Exception as e:
            return jsonify({"message": f"Error Retrieving Schedule Data: {str(e)}"})
        scheduler.add_monthly_scan(specific_time, date_selected, description, website_id, scan_url)

    return jsonify({
        "message": "Schedule triggered successfully"
    })

# shows the schedule for a site
@app.route('/api/website/<website_id>/schedule-scan/show-scans', methods=['POST'])
@api_key_required
def api_get_schedules(website_id):
    # owner and admin can access all websites
    priv_users = ['owner', 'admin']
    user_id = g.current_user_id
    website_auth_query = "SELECT * FROM website_auth WHERE website_id = %s AND user_id = %s"
    auth_result = db.query(website_auth_query, [website_id, user_id])
    role_query = "SELECT role FROM users WHERE user_id = %s"
    role = db.query(role_query, [user_id])[0]['role']
    # checks to see if the user has access to site or they are an owner or admin role
    if ((auth_result == []) and (role not in priv_users)):
        return jsonify({'message': "You don't have access to view scans on this website"}), 401
    schedules = scheduler.get_website_schedules(website_id)
    return jsonify(schedules)

# deletes a schedule from the website
@app.route('/api/website/<website_id>/schedule-scan/delete-schedule/<schedule_id>', methods=['POST'])
@api_key_required
def api_delete_schedule(website_id, schedule_id):
    # owner and admin can access all websites
    priv_users = ['owner', 'admin']
    user_id = g.current_user_id
    website_auth_query = "SELECT * FROM website_auth WHERE website_id = %s AND user_id = %s"
    auth_result = db.query(website_auth_query, [website_id, user_id])
    role_query = "SELECT role FROM users WHERE user_id = %s"
    role = db.query(role_query, [user_id])[0]['role']
    # checks to see if the user has access to site or they are an owner or admin role
    if ((auth_result == []) and (role not in priv_users)):
        return jsonify({'message': "You don't have access to delete schedules on this website"}), 401
    scheduler.delete_schedule(schedule_id)
    return jsonify("Your schedule has been deleted!")



# Injects user role into html layouts
@app.context_processor
def inject_id():
    return {'role': getRole()}


# Route to login page
@app.route('/login')
def login():
    next_page = request.args.get("next_page")
    return render_template('login.html', user=getUser(), next_page=next_page)


# Pop email from session and send user to home page
@app.route('/logout')
def logout():
    session.pop('email', default=None)
    return redirect('/')


# Logic to process a user login from form fields
@app.route('/processlogin', methods=["POST", "GET"])
def processlogin():
    # Get info from request and put into dict
    form_fields = dict((key, request.form.getlist(key)[0]) for key in list(request.form.keys()))

    # Authenticate login info
    auth = db.authenticate(form_fields['email'], form_fields['password'])

    # If login info matches, set session email to encrypted email and return success
    if auth:
        session['email'] = db.reversibleEncrypt('encrypt', form_fields['email'])
        return json.dumps({'success': 1})

    # If login doesn't match, return fail
    else:
        return json.dumps({'success': 0})


#######################################################################################
# OTHER
#######################################################################################
@app.route('/')
def root():
    return redirect('/home')


# Lightweight health check (no DB / auth) for container + platform probes.
@app.route('/healthz')
def healthz():
    return {"status": "ok"}, 200


# Route for home page, contains flash message logic
@app.route('/home', methods=["POST", "GET"])
def home():
    if request.method == "POST":
        if getRole() == 'unknown':
            return redirect(url_for("login", next_page=request.url))
        elif getRole() != 'owner' and getRole() != 'admin':
            flash("You do not have enough privilege to perform a scan.", "fail")
            return redirect(url_for('home', user=getUser()))
        else:
            return redirect(url_for('register', user=getUser()))

    return render_template('home.html', user=getUser())


# Route for settings page, contains post request logic for update and deletion features
@app.route('/settings', methods=["POST", "GET"])
def settings():
    # Get user and domain info from db
    users = db.query("SELECT user_id, email, role FROM users")
    domains = db.query("SELECT domain FROM domains ORDER BY domain")

    post_served = False

    # If we are serving a post request
    if request.method == "POST":
        # If we are updating user roles
        if 'update_roles' in request.form:
            to_flash = False

            # Get new role for every user
            for user in users:
                new_role = request.form.get(f"role_{str(user['user_id'])}")

                # Make sure owner role cant be changed or user cant change their own role
                if user['role'] == 'owner' or user['email'] == getUser():
                    continue

                # Make sure owner cant be changed
                if new_role == 'owner':
                    flash("Owner role cannot be changed", "fail")
                    continue

                # If new role is not current role, update role
                if new_role and new_role != user['role']:
                    try:
                        db.query(f"UPDATE users SET role = '{new_role}' WHERE user_id = '{user['user_id']}'")
                        users = db.query("SELECT user_id, email, role FROM users")
                        to_flash = True
                    except Exception as e:
                        flash(f"Error updating roles: {e}", "fail")

            if to_flash:
                flash("User roles updated successfully.", "success")

        # If we are adding a domain, get new domain
        elif 'add_domain' in request.form:
            new_domain = request.form.get('new_domain').strip().lower()

            # edge case checking
            if not new_domain:
                flash("Domain name cannot be empty.", "fail")
            elif '.' not in new_domain:
                flash("Invalid domain format.", "fail")
            else:
                # if domain not already authorized, add to db
                existing = db.query("SELECT 1 FROM domains WHERE domain = %s", [new_domain])
                if existing:
                    flash(f"Domain '{new_domain}' already exists.", "fail")
                else:
                    try:
                        db.query("INSERT INTO domains (domain) VALUES (%s)", [new_domain])
                        flash(f"Domain '{new_domain}' added successfully.", "success")
                        post_served = True
                        domains = db.query("SELECT domain FROM domains ORDER BY domain")
                    except Exception as e:
                        flash(f"Error adding domain '{new_domain}': {e}", "fail")

        # If we are deleting a domain, get domain to delete
        elif 'delete_domain' in request.form:
            to_delete = request.form.get('delete_domain')
            if to_delete:
                try:
                    # Make sure domain is in db, then try to delete
                    exists = db.query("SELECT 1 FROM domains WHERE domain = %s", [to_delete])
                    if not exists:
                        flash(f"Domain '{to_delete}' not found.", "fail")
                    else:
                        db.query("DELETE FROM domains WHERE domain = %s", [to_delete])
                        flash(f"Domain '{to_delete}' deleted successfully.", "success")
                        post_served = True
                        domains = db.query("SELECT domain FROM domains ORDER BY domain")
                except Exception as e:
                    flash(f"Error deleting domain '{to_delete}': {e}", "fail")

            else:
                flash("Invalid request to delete domain.", "fail")

        # If we are deleting a user, get user
        elif 'delete_user' in request.form:
            to_delete_id = request.form.get('delete_user')
            to_delete_email = db.query("SELECT email FROM users WHERE user_id=%s", [to_delete_id])[0]['email']
            if to_delete_email != []:
                message, status = delete_user_sitewide(to_delete_id, to_delete_email)
                users = db.query("SELECT user_id, email, role FROM users")
                post_served = True
                flash(message, status)
            else:
                flash(f"User: '{to_delete}' does not exist")

        elif 'generate-api-key' in request.form:
            try:
                user_email = request.form.get('generate-api-key')
                user_id_query = "SELECT user_id FROM users WHERE email = %s"
                user_id = db.query(user_id_query, [user_email])[0]['user_id']
                api_key = secrets.token_hex(32)
                db.generate_api_key(user_id=user_id, api_key=api_key)
                flash(f"Your API Key: {api_key}", "success")
                redirect(url_for('settings'))
                post_served = True
            except:
                flash("Failed to generate your API Key", "fail")

        # if we served a post request, refresh page
        if post_served:
            return redirect(url_for('settings'))

    return render_template('settings.html', user=getUser(), users=users, domains=domains)


def delete_user_sitewide(user_to_delete_id, user_to_delete_email):
    status = "success"
    try:
        webs_to_delete = db.query("SELECT website_id FROM websites WHERE owner_id = %s", [user_to_delete_id])
        for web_id in webs_to_delete:
            deleteWebsite(web_id['website_id'])
        db.query("DELETE FROM website_auth WHERE user_id = %s", [user_to_delete_id])
        db.query("DELETE FROM users WHERE user_id = %s", [user_to_delete_id])
        message = (f"User '{user_to_delete_email}' deleted successfully.")
    except Exception as e:
        status = "fail"
        message = f"Error deleting user '{user_to_delete_email}"
    return message, status

# Route for registering a new website group
@app.route("/register")
@login_required
def register():
    return render_template("register.html", user=getUser())


# Route for about page
@app.route("/about")
@login_required
def about():
    return render_template("about.html", user=getUser())


# route for solutions page
@app.route("/solutions")
@login_required
def solutions():
    return render_template("solutions.html", user=getUser())

def add_user(email, website_id):
    # adding website_name to auth why?
    website_name_query = "SELECT website_name FROM websites WHERE website_id = %s"
    website_name = db.query(website_name_query, [website_id])[0]['website_name']
    status = "Fail"
    try:
        user_info = db.query(f"SELECT user_id, role FROM users WHERE email = '{email}'")[0]
    except IndexError:
        user_info = 'unknown'

    if user_info != 'unknown':
        existing = db.query(f"SELECT * FROM website_auth WHERE website_id = {str(website_id)}")
        exist_bool = False
        for row in existing:
            if user_info['user_id'] == row['user_id']:
                exist_bool = True

        if not exist_bool:
            columns = ['website_id', 'user_id', 'role', 'website_name']
            values = [[website_id, user_info['user_id'], user_info['role'], website_name]]
            db.insertRows(table='website_auth', columns=columns, parameters=values)
            message = f"Website group shared with {email}"
            status = "Success"
        else:
            message = "Website group already shared with this user."

    else:
        message = "The email you provided is not registered with us."
        
    return message, status

def delete_user(user_id_to_delete_info, website_id):
    status = "fail"
    if user_id_to_delete_info:
                try:
                    db.query("DELETE FROM website_auth WHERE user_id = %s AND website_id = %s", [user_id_to_delete_info['user_id'], website_id])
                    message = f"User '{user_id_to_delete_info['email']}' removed successfully."
                    status = "success"
                except Exception as e:
                    message = f"Error removing user '{user_id_to_delete_info['email']}': {e}"

    else:
        message = "Invalid request to remove user."
    return message, status

# Route to render website.html
# Also handles logic for authorized access and adding and removing a user from the website group.
@app.route("/website/<website_id>", methods=["POST", "GET"])
@login_required
def website(website_id):
    query = "SELECT * FROM websites WHERE website_id = %s"
    website_data = db.query(query, [str(website_id)])

    user_email = getUser()
    user = db.query(f"SELECT user_id, role FROM users WHERE email = '{user_email}'")[0]

    guest_result = db.query(
        f"SELECT * FROM website_auth WHERE user_id = {str(user['user_id'])} AND website_id={str(website_id)}")
    owner_result = db.query(
        f"SELECT * FROM websites WHERE owner_id = {str(user['user_id'])} AND website_id={str(website_id)}")

    if (len(guest_result) == 0 and len(owner_result) == 0) and (user['role'] != 'owner' and user['role'] != 'admin'):
        flash("You do not have access to this website group")
        return render_template("home.html", user=getUser())

    # logic to manage users in a website group and handle edge cases
    if request.method == "POST":
        if 'add_user' in request.form:
            email = request.form.get("share_email")
            message, status= add_user(email, website_id)
            flash(message, status)       

        elif 'delete_user' in request.form:
            user_id_to_delete = ast.literal_eval(request.form.get('delete_user'))
            message, status= delete_user(user_id_to_delete, website_id)
            flash(message, status)

    # query to get all users with access to website
    access_list = db.query(f"""SELECT u.email, u.user_id, 'Owner' AS access_type FROM users u JOIN websites w ON u.user_id = w.owner_id WHERE w.website_id = {str(website_id)}
             UNION SELECT u.email, u.user_id, CASE WHEN u.user_id = w_owner.owner_id THEN 'Owner' ELSE 'Authorized' END as access_type FROM users u 
             JOIN website_auth wa ON u.user_id = wa.user_id LEFT JOIN websites w_owner ON wa.website_id = w_owner.website_id WHERE wa.website_id = {str(website_id)}""")
    
    if website_id:
        return render_template("website.html", user=getUser(), website_data=website_data, access_list=access_list)
    else:
        return "Website not found"


# handles creating a url for each website's scheduling page
@app.route("/website/<website_id>/schedule-scan")
def website_scan(website_id):
    # gets websites id data and embeds it into page
    query = "SELECT * FROM websites WHERE website_id = %s"
    website_data = db.query(query, [str(website_id)])
    if website_id:
        return render_template("schedule-scan.html", user=getUser(), website_data=website_data)
    else:
        return "Website not found"


# preprocessing format for hourly scan
def hourly_scan(frequency, start_time, end_time):
    frequency = int(frequency)
    run_times = []
    start_minute_str = start_time[3:]
    end_minute_str = end_time[3:]
    start_hour_str = start_time[:2]
    start_hour_int = int(start_hour_str)
    # checks if scan should run on the last hour
    if int(end_minute_str) >= int(start_minute_str):
        end_hour_int = int(end_time[:2])
    else:
        end_hour_int = int(end_time[:2]) - 1
    # checks the amount of runs that should occur between given times
    hour_differential = end_hour_int - start_hour_int
    runs = int(mth.floor(hour_differential) / frequency)
    # gets each time in minutes
    for i in range(0, runs + 1):
        hour = frequency * i + start_hour_int
        run_time_str = f"{hour}:{start_minute_str}"
        run_times.append(run_time_str)
    return run_times


# helper function to capitalize each day
def capitalizeDays(days_to_run):
    days_capitalized = []
    for day in days_to_run:
        days_capitalized.append(day.capitalize())
    return days_capitalized


# puts schedule into scheduler
@app.route("/scheduleScan", methods=["POST", "GET"])
def schedule_scan():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data"}), 400
    print("Hi", data)
    # always going to have this data
    time_interval = data.get("time_interval")
    scan_url = data.get("website_url")
    website_id = data.get("website_id")
    description = data.get("description")

    # checks the type of scan
    if time_interval == "hourly":
        # unpackage data depending on data
        try:
            frequency, start_time, end_time, days_to_run = data.get("frequency"), data.get("start_time"), data.get(
                "end_time"), data.get("days_to_run")
        except Exception as e:
            return jsonify({"message": f"Error Retrieving Schedule Data: {str(e)}"})
        # captalize days so that it is compatiable with datetime format in scheduler
        days_capitalized = capitalizeDays(days_to_run)
        # gets the proper run times for hourly scans
        run_times = hourly_scan(frequency, start_time, end_time)
        # passes data for scheduler
        print(frequency, days_capitalized, run_times, description, website_id, scan_url)
        scheduler.add_hourly_scan(frequency, days_capitalized, run_times, description, website_id, scan_url)

    if (time_interval == "daily") or (time_interval == "weekly"):
        try:
            specific_time, days_to_run = data.get("specific_time"), data.get("days_to_run")
        except Exception as e:
            return jsonify({"message": f"Error Retrieving Schedule Data: {str(e)}"})
        days_capitalized = capitalizeDays(days_to_run)
        scheduler.add_daily_or_weekly_scan(days_capitalized, specific_time, description, website_id, scan_url,
                                           time_interval)

    if time_interval == "monthly":
        try:
            specific_time, date_selected = data.get("specific_time"), data.get("date_selected")
        except Exception as e:
            return jsonify({"message": f"Error Retrieving Schedule Data: {str(e)}"})
        scheduler.add_monthly_scan(specific_time, date_selected, description, website_id, scan_url)

    return jsonify({
        "message": "Schedule triggered successfully"
    })


# gets data to load in about schedules for a website_id
@app.route("/api/websites/schedules", methods=["GET"])
def api_website_schedules():
    website_id = request.args.get("website_id")
    schedules = scheduler.get_website_schedules(website_id)
    return jsonify(schedules)


# deletes a schedule with a schedule_id from the db
@app.route("/deleteSchedule", methods=["GET"])
def delete_schedule():
    schedule_id = request.args.get("schedule_id")
    scheduler.delete_schedule(schedule_id)
    return jsonify("Your schedule has been deleted!")


# Deletes a website group and all associated scans / scan data from the db
@app.route("/deleteWebsite", methods=["POST", "GET"])
def deleteWebsite(website_id=None):
    if website_id is None:
        data = request.get_json()
        website_id = data.get("website_id")
        if not data:
            return jsonify({"error": "No JSON data"}), 400

    get_scans_query = "SELECT * FROM scans WHERE website_id = %s"
    scans = db.query(get_scans_query, [website_id])
    # This can be sped up: delete all scans at same time (one query)
    for scan in scans:
        deleteScan(scan["scan_id"])
    schedules = scheduler.get_website_schedules(website_id)
    for schedule in schedules:
        scheduler.delete_schedule(schedule["schedule_id"])
    delete_website_users_query = "DELETE FROM website_auth WHERE website_id = %s"
    db.query(delete_website_users_query, [website_id])
    delete_website_query = "DELETE FROM websites WHERE website_id = %s"
    db.query(delete_website_query, [website_id])
    return redirect(url_for('home'))


# Deletes an individual scan in a website group from the db
@app.route("/deleteScan", methods=["POST", "GET"])
def deleteScan(scan_id=None):
    if scan_id is None:
        flash_message = True
        data = request.get_json()
        scan_id = data.get("scan_id")
        if not data:
            return jsonify({"error": "No JSON data"}), 400

    delete_vulnerabilities_query = "DELETE FROM vulnerabilities WHERE scan_id = %s"
    db.query(delete_vulnerabilities_query, [scan_id])
    delete_scanned_websites_query = "DELETE FROM scanned_websites WHERE scan_id = %s"
    db.query(delete_scanned_websites_query, [scan_id])
    delete_scan_query = "DELETE FROM scans WHERE scan_id = %s"
    db.query(delete_scan_query, [scan_id])
    # This return is only so flask doesn't throw a no return error
    return jsonify({'Deleted_Scan': scan_id})


# Wrapper function to trigger a scan on the pipeline
@app.route("/triggerScan", methods=["POST", "GET"])
def trigger():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data"}), 400

    # Readers are view-only and cannot start scans.
    if getRole() == 'reader':
        return jsonify({"error": "Readers have view-only access and cannot start scans."}), 403

    scan_name = data.get("scan_name")
    scan_url = data.get("scan_url")
    website_id = data.get("website_id")
    user_id = db.query(f"SELECT DISTINCT user_id FROM users WHERE email = '{str(getUser())}'")[0]['user_id']
    return (run_scan(scan_name, scan_url, website_id, db, user_id))

# Route to insert new website data into db from /register
@app.route("/registerWebsite", methods=["POST", "GET"])
def register_website_frontend():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data"}), 400

    query = "SELECT user_id FROM users WHERE email = %s"
    values = [getUser()]
    user_id = (db.query(query, values)[0]['user_id'])
    website_name = data.get("scan_name")
    website_url = data.get("scan_url")
    return(register_website(user_id, website_name, website_url))

def register_website(user_id, website_name, website_url):
    website_query = "SELECT * FROM websites WHERE website_url = %s"
    websites = db.query(website_query, [website_url])
    if not websites:
        columns = ['owner_id', 'website_name', 'website_url']
        values = [[user_id, website_name, website_url]]
        website_id = db.insertRows(table='websites', columns=columns, parameters=values)
        return jsonify({
            "message": "Website created!",
            "site name": website_name,
            "website url": website_url,
            "website_id": website_id
        })
    return jsonify({
        "message": "Website already exists"
    })


# creates the scans directory in the working directory
base_scans_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scans')
os.makedirs(base_scans_dir, exist_ok=True)


def status(pipeline_id):
    """Refresh a scan's status from the GitHub Actions backend (no-op if disabled)."""
    if pipeline_id in (None, '-1', -1):
        return None
    scan = db.query("SELECT * FROM scans WHERE pipeline_id = %s", [pipeline_id])
    if scan:
        return refresh_scan_status(scan[0], db)
    return None


# Cancels the currently running scan
@app.route("/cancelScan", methods=["POST", "GET"])
def cancel_scan():
    return cancel_scan_run(db)


# Frontend wrapper for pulling website group data from db to dashboard.html
@app.route("/api/websites", methods=["GET"])
def frontend_website_api():
    # gets the id of the user
    user_email = getUser()
    user_query = "SELECT user_id FROM users WHERE email = %s"
    user_id = (db.query(user_query, [user_email])[0]['user_id'])
    return jsonify(get_dashboard_sites(user_id))


# Retrieve all websites the user has access to from db
def get_dashboard_sites(user_id):
    results = []
    role_query = "SELECT role FROM users WHERE user_id = %s"
    user_role = (db.query(role_query, [user_id])[0]['role'])
    # get the sites the user can access

    if user_role == 'owner' or user_role == 'admin':
        website_query = "SELECT * FROM websites ORDER BY website_name"
        websites = (db.query(website_query))
    else:
        website_query = "SELECT * FROM websites WHERE owner_id = %s ORDER BY website_name"
        share_query = db.query(f"SELECT * FROM website_auth WHERE user_id = {str(user_id)} ORDER BY website_name")
        websites = (db.query(website_query, [user_id]))

    # crudely append shared websites to website list
    if (user_role != 'owner' and user_role != 'admin') and len(share_query) != 0:
        for item in share_query:
            websites.append(item)
    # gets all pipelines that aren't finished
    # checks status of all the pipelines
    # get the latest scan from each website

    for website in websites:
        website_id = (website['website_id'])

        # Refresh any in-flight scans for this website from the scan backend.
        unfinished_query = "SELECT pipeline_id FROM scans WHERE website_id = %s AND status IN ('pending', 'queued', 'running', 'created', 'in_progress')"
        for pipeline in db.query(unfinished_query, [website_id]):
            status(pipeline['pipeline_id'])

        query = "SELECT * FROM scans WHERE website_id = %s ORDER BY scan_id DESC LIMIT 1"
        scan = db.query(query, [website_id])
        if len(scan) == 0:
            scan = {'date': 'No Scans Run', 'status': 'N/A', 'pipeline_id': '-1', 'informational_risks': '-',
                    'low_risks': '-', 'medium_risks': '-', 'high_risks': '-'}
            website_result = {**website, **scan}
        else:
            website_result = {**website, **scan[0]}
        results.append(website_result)
    return results


# Frontend wrapper for retrieving individual scans to display on website.html
@app.route("/api/websites/scans", methods=["GET"])
def frontend_website_scans():
    website_id = request.args.get("website_id")
    results = get_website_scans(website_id)
    return results


# Retrieve all scans relating to that website group
def get_website_scans(website_id):
    query = "SELECT * FROM scans WHERE website_id = %s AND status IN ('pending', 'queued', 'running', 'created', 'in_progress')"
    unfinished_pipelines = (db.query(query, [website_id]))
    for pipeline in unfinished_pipelines:
        status(pipeline['pipeline_id'])
    query = "SELECT * FROM scans WHERE website_id = %s ORDER BY scan_id DESC"
    results = db.query(query, [website_id])
    return results


# Grabs website and scan information and passes it to /report
@app.route("/processreportdata", methods=["POST"])
def process_data():
    try:
        data = request.get_json()
        session["website_id"] = data.get("website_id", "Unknown")
        session["website_name"] = data.get("website_name", "Unknown")
        session["scan_id"] = data.get("scan_id", "Unknown")

        return jsonify({"redirect_url": url_for("report")})

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Check user permissions and pass relevant website data to report.html
@app.route("/report/<scan_id>")
@login_required
def report(scan_id):
    try:
        # Get scan data with website name
        scan_query = """
            SELECT s.*, w.website_name 
            FROM scans s 
            JOIN websites w ON s.website_id = w.website_id 
            WHERE s.scan_id = %s
        """
        scan_data = db.query(scan_query, [scan_id])

        if not scan_data:
            flash("Scan not found", "fail")
            return redirect(url_for("dashboard"))

        # Get user permissions for this website
        user = db.query(f"SELECT user_id, role FROM users WHERE email = '{getUser()}'")[0]
        website_id = scan_data[0]['website_id']

        # Check if user has access to this website (as owner or shared)
        owner_result = db.query("SELECT * FROM websites WHERE owner_id = %s AND website_id = %s",
                                [str(user['user_id']), str(website_id)])
        guest_result = db.query("SELECT * FROM website_auth WHERE user_id = %s AND website_id = %s",
                                [str(user['user_id']), str(website_id)])

        if len(owner_result) == 0 and len(guest_result) == 0:
            if user['role'] == 'owner' or user['role'] == 'admin':
                pass
            else:
                flash("You do not have access to this scan report", "fail")
                return redirect(url_for("home"))

        data = {
            'website_id': scan_data[0]['website_id'],
            'website_name': scan_data[0]['website_name'],
            'scan_id': scan_id,
            'scan_date': scan_data[0]['scan_date']
        }

        return render_template("report.html", user=getUser(), report_data=data)

    except Exception as e:
        app.logger.error(f"Error loading report: {str(e)}")
        flash(f"Error loading report: {str(e)}", "fail")
        return redirect(url_for("dashboard"))


# Route to render dashboard.html
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", user=getUser())


@app.route("/static/<path:path>")
def static_dir(path):
    return send_from_directory("static", path)


@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, public, max-age=0"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    return r


# Initiate Oauth sign in
@app.route('/login/google')
def login_google():
    # this initiates Google OAuth flow then calls to authoruze/google
    try:
        redirect_uri = url_for('authorize_google', _external=True)
        # next_page = request.args.get('next_page', default=url_for('home'))
        return google.authorize_redirect(redirect_uri)
    except Exception as e:
        app.logger.error(f"Error during Google login: {str(e)}")
        return "Error occurred during Google login", 500


# finalizes Oauth flow, stores users email in session, and redirects to home
@app.route('/authorize/google')
def authorize_google():
    try:
        token = google.authorize_access_token()
        userinfo_endpoint = google.server_metadata['userinfo_endpoint']
        resp = google.get(userinfo_endpoint)
        user_info = resp.json()

        email = user_info.get('email')
        if not email:
            return "No email returned from Google", 400

        domains = db.query("SELECT domain FROM domains")
        email_domain = email.split('@')[1]
        authorized = False

        for domain in domains:
            if email_domain.lower() == domain['domain']:
                authorized = True

        if authorized:
            session['email'] = db.reversibleEncrypt('encrypt', email)
            users = db.query("SELECT user_id FROM users WHERE email = %s", [email])
            if not users:
                api_key = secrets.token_hex(32)
                db.createUser(email, role='reader', api_key=api_key)

        else:
            flash("Your domain is not authorized to access this website.")

        return redirect(url_for('home'))

    except Exception as e:
        app.logger.error(f"Error during Google authorization: {str(e)}")
        return "Error occurred during Google authorization", 500


@app.route('/generateKey', methods=['POST'])
def add_key():
    user_id = request.form.get('user_id')
    api_key = secrets.token_hex(32)
    db.generate_api_key(user_id=user_id, api_key=api_key)
    return f"User {user_id} API Key: {api_key}", 200


# Logic to handle downloading raw scan data
@app.route("/api/download_scan_json/<scan_id>", methods=["GET"])
@login_required
def download_scan_json(scan_id):
    try:
        # Verify scan is in database
        scan_data = db.query("SELECT * FROM scans WHERE scan_id = %s", [scan_id])
        if not scan_data:
            return jsonify({"error": "Scan not found"}), 404

        # Get scan metadata from database
        scan_record = scan_data[0]
        pipeline_id = scan_record['pipeline_id']
        website_url = scan_record['website_url']
        scan_status = scan_record['status']

        if scan_status not in ["success", "Success", "Completed"]:
            app.logger.warning(f"Attempting to download incomplete scan {scan_id} with status {scan_status}")

        # Locate base directory where scan files are stored
        base_scans_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scans')

        if not os.path.exists(base_scans_dir):
            return jsonify({"error": "Scans directory not found"}), 404

        json_file_path = None

        # First check expected location based on pipeline_id
        pipeline_dir = os.path.join(base_scans_dir, str(pipeline_id))
        if os.path.exists(pipeline_dir):
            json_files = glob.glob(os.path.join(pipeline_dir, "**", "*.json"), recursive=True)
            if json_files:
                json_file_path = json_files[0]
                app.logger.info(f"Found JSON file in expected pipeline directory: {json_file_path}")

        # Second look through all scan directories if file not found in expected location
        if not json_file_path:
            scan_dirs = [d for d in os.listdir(base_scans_dir) if os.path.isdir(os.path.join(base_scans_dir, d))]
            scan_dirs.sort(reverse=True)

            app.logger.info(f"Looking for scan data in directories: {scan_dirs}")

            for dir_name in scan_dirs:
                dir_path = os.path.join(base_scans_dir, dir_name)
                json_files = glob.glob(os.path.join(dir_path, "**", "*.json"), recursive=True)

                if json_files:
                    json_file_path = json_files[0]
                    app.logger.info(f"Found JSON file in directory {dir_name}: {json_file_path}")

                    # Update database with correct pipeline_id if it was found in a different directory
                    try:
                        db.query("UPDATE scans SET pipeline_id = %s WHERE scan_id = %s", [dir_name, scan_id])
                        app.logger.info(f"Updated scan {scan_id} to use pipeline_id {dir_name}")
                    except Exception as e:
                        app.logger.error(f"Failed to update pipeline ID: {str(e)}")

                    break

        # Return error if no JSON is found
        if not json_file_path:
            return jsonify({
                "error": "No scan data found for this website.",
                "details": f"Looking for scan {scan_id} (pipeline {pipeline_id}) for website {website_url}",
                "available_dirs": scan_dirs if 'scan_dirs' in locals() else []
            }), 404

        app.logger.info(f"Serving JSON file: {json_file_path}")
        return send_file(json_file_path, as_attachment=True,
                         download_name=f"scan_{scan_id}_{website_url.replace('://', '_').replace('/', '_')}.json")

    except Exception as e:
        app.logger.error(f"Error downloading scan JSON: {str(e)}")
        return jsonify({
            "error": f"Error downloading scan JSON: {str(e)}",
            "debug_url": f"/api/debug/scan_files/{scan_id}"
        }), 500


# search for website name
@app.route("/search")
@login_required
def search():
    query = request.args.get("q", "").strip()
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    status = request.args.get("status")
    # filter for risks checkbox
    show_high = request.args.get("show_high") == "true"
    show_medium = request.args.get("show_medium") == "true"
    show_low = request.args.get("show_low") == "true"
    show_info = request.args.get("show_info") == "true"

    user_id = db.query("SELECT user_id FROM users WHERE email = %s", [getUser()])[0]['user_id']
    # queries the data base for filter
    sql_query = """
        SELECT w.website_id, w.website_name, w.website_url, s.scan_date, s.status, 
               s.high_risks, s.medium_risks, s.low_risks, s.informational_risks,
               (COALESCE(s.high_risks,0) + COALESCE(s.medium_risks,0) + COALESCE(s.low_risks,0) + COALESCE(s.informational_risks,0)) as total_risks
        FROM websites w
        LEFT JOIN (SELECT website_id, MAX(scan_date) as latest_date
            FROM scans
            GROUP BY website_id
        ) latest_scans ON w.website_id = latest_scans.website_id
        LEFT JOIN scans s ON s.website_id = latest_scans.website_id AND s.scan_date = latest_scans.latest_date
        WHERE w.owner_id = %s
    """

    params = [user_id]
    # checks for any and all queries requested
    if query:
        sql_query += " AND (w.website_name LIKE %s OR w.website_url LIKE %s)"
        params += [f"%{query}%", f"%{query}%"]

    if start_date:
        sql_query += " AND s.scan_date >= %s"
        params.append(start_date)

    if end_date:
        sql_query += " AND s.scan_date <= %s"
        params.append(end_date)

    if status:
        sql_query += " AND LOWER(s.status) = %s"
        params.append(status.lower())

    # dispalys the risks in order for which website has the highest of that amouint
    risk_conditions = []
    if show_high:
        risk_conditions.append("s.high_risks > 0")
    if show_medium:
        risk_conditions.append("s.medium_risks > 0")
    if show_low:
        risk_conditions.append("s.low_risks > 0")
    if show_info:
        risk_conditions.append("s.informational_risks > 0")

    if risk_conditions:
        sql_query += " AND (" + " OR ".join(risk_conditions) + ")"

    sql_query += " ORDER BY total_risks DESC, w.website_name ASC"

    results = db.query(sql_query, params)
    return jsonify(results)


@app.route("/api/dashboard/scan_comparison/<scan_id>", methods=["GET"])
@login_required
def api_dashboard_scan_comparison(scan_id):
    try:
        # Get current scan info
        current_scan = db.query("SELECT * FROM scans WHERE scan_id = %s", [scan_id])

        if not current_scan:
            return jsonify({"error": "Scan not found"}), 404

        website_id = current_scan[0]['website_id']
        scan_date = current_scan[0]['scan_date']

        # get all scans for this website
        all_website_scans = db.query("""
            SELECT * FROM scans 
            WHERE website_id = %s
            ORDER BY scan_date DESC
        """, [website_id])

        # Get previous scan for the same website
        previous_scan = db.query("""
            SELECT * FROM scans 
            WHERE website_id = %s AND scan_date < %s AND status = 'success'
            ORDER BY scan_date DESC
            LIMIT 1
        """, [website_id, scan_date])

        # Get vulnerability statistics for current scan
        current_vulns = db.query("""
            SELECT severity, COUNT(*) as count, SUM(count) as instances
            FROM vulnerabilities
            WHERE scan_id = %s
            GROUP BY severity
        """, [scan_id])

        # Initialize remediation metrics
        remediation_metrics = {
            "remediation_rate": 0,
            "new_issues": 0,
            "fixed_issues": 0,
            "change_high": 0,
            "change_medium": 0,
            "change_low": 0,
            "change_info": 0,
            "total_previous_vulns": 0,
            "total_current_vulns": 0
        }

        # If no previous scan, return only current scan data
        if not previous_scan:
            return jsonify({
                "current": current_scan[0],
                "previous": None,
                "current_vulns": current_vulns,
                "remediation_metrics": remediation_metrics
            })

        # Get vulnerability statistics for previous scan
        previous_scan_id = previous_scan[0]['scan_id']
        previous_vulns = db.query("""
            SELECT severity, COUNT(*) as count, SUM(count) as instances
            FROM vulnerabilities
            WHERE scan_id = %s
            GROUP BY severity
        """, [previous_scan_id])

        # Calculate remediation metrics
        current = current_scan[0]
        previous = previous_scan[0]

        # Calculate changes in risk levels
        change_high = previous['high_risks'] - current['high_risks']
        change_medium = previous['medium_risks'] - current['medium_risks']
        change_low = previous['low_risks'] - current['low_risks']
        change_info = previous['informational_risks'] - current['informational_risks']

        # Calculate total issues
        total_previous = previous['high_risks'] + previous['medium_risks'] + previous['low_risks'] + previous[
            'informational_risks']
        total_current = current['high_risks'] + current['medium_risks'] + current['low_risks'] + current[
            'informational_risks']

        # Positive changes indicate remediated issues
        fixed_issues = max(0, total_previous - total_current) if total_previous > total_current else 0
        new_issues = max(0, total_current - total_previous) if total_current > total_previous else 0

        remediation_rate = round((fixed_issues / total_previous) * 100) if total_previous > 0 else 0

        remediation_metrics = {
            "remediation_rate": remediation_rate,
            "new_issues": new_issues,
            "fixed_issues": fixed_issues,
            "change_high": change_high,
            "change_medium": change_medium,
            "change_low": change_low,
            "change_info": change_info,
            "total_previous_vulns": total_previous,
            "total_current_vulns": total_current
        }

        # Check if we can do a detailed vulnerability comparison
        # Get vulnerability names from both scans
        current_vuln_names = db.query("""
            SELECT vulnerability_name, severity, count
            FROM vulnerabilities
            WHERE scan_id = %s
        """, [scan_id])

        previous_vuln_names = db.query("""
            SELECT vulnerability_name, severity, count
            FROM vulnerabilities
            WHERE scan_id = %s
        """, [previous_scan_id])

        # Create maps for easier comparison
        current_map = {v['vulnerability_name']: v for v in current_vuln_names}
        previous_map = {v['vulnerability_name']: v for v in previous_vuln_names}

        # Identify new, fixed, and persistent vulnerabilities
        new_vulns = [name for name in current_map.keys() if name not in previous_map]
        fixed_vulns = [name for name in previous_map.keys() if name not in current_map]
        persistent_vulns = [name for name in current_map.keys() if name in previous_map]

        detailed_comparison = {
            "new_vulnerabilities": len(new_vulns),
            "fixed_vulnerabilities": len(fixed_vulns),
            "persistent_vulnerabilities": len(persistent_vulns),
            "new_vuln_list": [current_map[name] for name in new_vulns],
            "fixed_vuln_list": [previous_map[name] for name in fixed_vulns],
            "top_persistent": [current_map[name] for name in persistent_vulns[:5]]  # Top 5 persistent vulns
        }

        return jsonify({
            "all_website_scans": all_website_scans,
            "current": current_scan[0],
            "previous": previous_scan[0],
            "current_vulns": current_vulns,
            "previous_vulns": previous_vulns,
            "remediation_metrics": remediation_metrics,
            "detailed_comparison": detailed_comparison
        })

    except Exception as e:
        app.logger.error(f"Error calculating comparison: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/dashboard/website/<website_id>", methods=["GET"])
@login_required
def api_dashboard_website(website_id):
    try:
        # Get the user ID for permission checking
        user = db.query("SELECT user_id, role FROM users WHERE email = %s", [getUser()])[0]

        # Check if user has access to this website (as owner or shared)
        owner_result = db.query("SELECT * FROM websites WHERE owner_id = %s AND website_id = %s",
                                [str(user['user_id']), str(website_id)])
        guest_result = db.query("SELECT * FROM website_auth WHERE user_id = %s AND website_id = %s",
                                [str(user['user_id']), str(website_id)])

        if len(owner_result) == 0 and len(guest_result) == 0:
            if user['role'] == 'owner' or user['role'] == 'admin':
                pass
            else:
                return jsonify({"error": "Unauthorized access"}), 403

        # Get website data
        website_data = db.query("""
            SELECT 
                w.website_id,
                w.website_name,
                w.website_url,
                w.owner_id
            FROM websites w
            WHERE w.website_id = %s
        """, [website_id])

        if not website_data:
            return jsonify({"error": "Website not found"}), 404

        # Get latest scan data for this website
        latest_scan = db.query("""
            SELECT 
                s.scan_id,
                s.high_risks,
                s.medium_risks,
                s.low_risks,
                s.informational_risks,
                s.scan_date,
                s.status
            FROM scans s
            WHERE s.website_id = %s AND (s.status = 'Success' OR s.status = 'Completed')
            ORDER BY s.scan_date DESC
            LIMIT 1
        """, [website_id])

        # Combine website and scan data
        result = website_data[0]
        if latest_scan:
            for key, value in latest_scan[0].items():
                if key not in result:
                    result[key] = value

        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error getting website data: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/dashboard/scan_vulnerabilities/<scan_id>", methods=["GET"])
@login_required
def api_dashboard_scan_vulnerabilities(scan_id):
    try:
        vulnerabilities = db.query("""
            SELECT 
                vulnerability_name,
                severity,
                description,
                solution,
                SUM(count) AS count
            FROM vulnerabilities
            WHERE scan_id = %s
            GROUP BY vulnerability_name, severity, description, solution
            ORDER BY 
                CASE 
                    WHEN severity LIKE 'high%' THEN 1
                    WHEN severity LIKE 'medium%' THEN 2
                    WHEN severity LIKE 'low%' THEN 3
                    ELSE 4
                END,
                SUM(count) DESC
        """, [scan_id])

        return jsonify(vulnerabilities)
    except Exception as e:
        app.logger.error(f"Error getting vulnerabilities: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/trends/risk_scores/<website_id>/<scan_id>")
def api_risk_scores(website_id, scan_id):
    # Get risk scores for all completed scans up to the specified scan
    query = """
        SELECT s.scan_date AS scan_date, 
               (s.high_risks * 15 + s.medium_risks * 1 + s.low_risks * 0.1) / 10 AS risk_score,
               high_risks, medium_risks, low_risks, status

        FROM scans s
        WHERE website_id = %s
          AND (scan_id <= %s)
          AND (status = 'success' OR status = 'completed')
        ORDER BY s.scan_date
    """
    results = db.query(query, [website_id, scan_id])
    return jsonify(results)


@app.route("/api/trends/scan_activity/<website_id>/<scan_id>")
@login_required
def api_scan_activity(website_id, scan_id):
    # Get the count of scans performed per day grouped by date
    query = """
        SELECT DATE(scan_date) AS scan_day, COUNT(*) AS scan_count
        FROM scans
        WHERE website_id = %s AND scan_id <= %s
        GROUP BY scan_day
        ORDER BY scan_day
    """
    results = db.query(query, [website_id, scan_id])
    return jsonify(results)


@app.route("/api/trends/vulnerability_discovery/<website_id>/<scan_id>")
@login_required
def api_vulnerability_discovery(website_id, scan_id):
    # Track vulnerability discovery over time. joins scans with vulnerabilities and calculates total found per day
    query = """
        SELECT DATE(s.scan_date) AS date, SUM(v.count) AS total_discovered
        FROM scans s
        JOIN vulnerabilities v ON s.scan_id = v.scan_id
        WHERE s.website_id = %s
        AND DATE(s.scan_date) <= (
            SELECT DATE(scan_date) FROM scans WHERE scan_id = %s
        )
        GROUP BY DATE(s.scan_date)
        ORDER BY date
    """
    results = db.query(query, [website_id, scan_id])
    return jsonify(results)


@app.route("/api/trends/remediation_rate/<website_id>/<scan_id>")
@login_required
def api_remediation_rate_flat_series(website_id, scan_id):
    try:
        # Get current scan data
        current_scan = db.query("SELECT * FROM scans WHERE scan_id = %s", [scan_id])
        if not current_scan:
            return jsonify([])

        scan_date = current_scan[0]['scan_date']

        # Find the previous successful scan to compare against
        previous_scan = db.query("""
            SELECT * FROM scans 
            WHERE website_id = %s AND scan_date < %s AND status = 'success'
            ORDER BY scan_date DESC
            LIMIT 1
        """, [website_id, scan_date])

        if not previous_scan:
            return jsonify([])

        current = current_scan[0]
        previous = previous_scan[0]

        # Calculate total vulnerabilities for current and previous scans
        total_current = current['high_risks'] + current['medium_risks'] + current['low_risks'] + current[
            'informational_risks']
        total_previous = previous['high_risks'] + previous['medium_risks'] + previous['low_risks'] + previous[
            'informational_risks']

        # Calculate remediation rate as percentage of fixed vulnerabilities
        remediated = total_previous - total_current
        remediation_rate = round((remediated / total_previous) * 100) if total_previous > 0 else 0

        # Get all scan dates up to the current scan for timeline display
        scan_dates = db.query("""
            SELECT scan_date FROM scans 
            WHERE website_id = %s AND scan_date <= %s 
            ORDER BY scan_date
        """, [website_id, scan_date])

        # Create flat trend series with the same remediation rate for all dates
        results = [{
            "scan_date": row["scan_date"],
            "remediation_rate": remediation_rate
        } for row in scan_dates]

        return jsonify(results)

    except Exception as e:
        app.logger.error(f"Error generating flat remediation trend: {str(e)}")
        return jsonify([])


@app.route("/api/dashboard/scanned_websites/<scan_id>", methods=["GET"])
@login_required
def api_dashboard_scanned_websites(scan_id):
    try:
        # First get all websites for this scan
        websites_query = """
            SELECT website_url 
            FROM scanned_websites 
            WHERE scan_id = %s
        """
        websites = db.query(websites_query, [scan_id])

        # Create a result array to hold our final data
        result = []

        # For each website, get its associated vulnerabilities
        for website in websites:
            website_url = website['website_url']

            # Query vulnerabilities for this specific website URL
            vuln_query = """
                SELECT vulnerability_name 
                FROM vulnerabilities 
                WHERE scan_id = %s AND instance_url = %s
            """
            vulnerabilities = db.query(vuln_query, [scan_id, website_url])

            # Add entry to our result set
            if vulnerabilities:
                for vuln in vulnerabilities:
                    result.append({
                        'website_url': website_url,
                        'vulnerability_name': vuln['vulnerability_name']
                    })
            else:
                # If no vulnerabilities found for this website
                result.append({
                    'website_url': website_url,
                    'vulnerability_name': 'None'
                })

        return jsonify(result), 200
    except Exception as e:
        app.logger.error(f"Error fetching scanned websites for scan {scan_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/report/risk_score_by_website/<website_id>/<scan_id>', methods=['GET'])
@login_required
def risk_score_by_website(website_id, scan_id):
    try:
        # Calculate risk scores for each scanned website
        query = """
            SELECT 
                ss.website_url AS website_name,
                COALESCE(SUM(CASE WHEN v.severity LIKE 'high%' THEN v.count ELSE 0 END), 0) AS high_risks,
                LEAST(100, ROUND(
                     (COALESCE(SUM(CASE WHEN v.severity LIKE 'high%' THEN v.count ELSE 0 END), 0) * 25 +
                      COALESCE(SUM(CASE WHEN v.severity LIKE 'medium%' THEN v.count ELSE 0 END), 0) * 10 +
                      COALESCE(SUM(CASE WHEN v.severity LIKE 'low%' THEN v.count ELSE 0 END), 0) * 2
                     ) / 10.0
                )) AS risk_score
            FROM scanned_websites ss
            JOIN scans s ON ss.scan_id = s.scan_id
            LEFT JOIN vulnerabilities v 
                ON ss.scan_id = v.scan_id AND v.instance_url = ss.website_url
            WHERE s.website_id = %s
              AND s.scan_id = %s
            GROUP BY ss.website_url;
        """
        results = db.query(query, [website_id, scan_id])
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/report/high_risk_by_website/<website_id>/<scan_id>', methods=['GET'])
@login_required
def high_risk_by_website(website_id, scan_id):
    try:
        # Get high risk vulnerability counts for each scanned website
        # Group by website URL and calculates sum of high severity vulnerabilities
        query = """
            SELECT 
                ss.website_url AS website_name,
                COALESCE(SUM(
                    CASE WHEN v.severity LIKE 'high%%' THEN v.count ELSE 0 END
                ), 0) AS high_risks
            FROM scanned_websites ss
            JOIN scans s ON ss.scan_id = s.scan_id
            LEFT JOIN vulnerabilities v 
                ON ss.scan_id = v.scan_id 
                AND v.instance_url = ss.website_url
            WHERE s.website_id = %s
              AND s.scan_id = %s
            GROUP BY ss.website_url
        """
        results = db.query(query, [website_id, scan_id])
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
