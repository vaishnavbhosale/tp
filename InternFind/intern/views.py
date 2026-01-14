from urllib import request
from django.urls import reverse
from django.forms import ValidationError
from django.shortcuts import render, redirect
from . models import *
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from datetime import date
from django.contrib import messages
from django.utils.datastructures import MultiValueDictKeyError
from django.db.models import Q  # <--- Essential for search functionality

def index(request):
    return render(request, "index.html")

def user_login(request):
    if request.user.is_authenticated:
        return redirect("/")
    
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)

        if user is not None:
            try:
                # Check if this user is actually an Applicant
                user1 = Applicant.objects.get(user=user)
                if user1.type == "applicant":
                    login(request, user)
                    return redirect("/user_homepage")
            except Applicant.DoesNotExist:
                # If the user exists but isn't an Applicant (e.g., Admin or Company)
                if user.is_staff:
                    messages.error(request, "Admins must log in via the Admin Portal.")
                else:
                    messages.error(request, "No Applicant account found for this user.")
                return render(request, "user_login.html")
        else:
            # Invalid password or username
            thank = True
            return render(request, "user_login.html", {"thank": thank})

    return render(request, "user_login.html")

def user_homepage(request):
    if not request.user.is_authenticated:
        return redirect('/user_login/')
    
    applicant = Applicant.objects.get(user=request.user)
    
    if request.method == "POST":   
        email = request.POST.get('email', '')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        phone = request.POST.get('phone', '')
        gender = request.POST.get('gender', '')
        
        # 👇 CAPTURE SKILLS HERE
        skills = request.POST.get('skills', '') 

        applicant.user.email = email
        applicant.user.first_name = first_name
        applicant.user.last_name = last_name
        applicant.phone = phone
        applicant.gender = gender
        
        # 👇 SAVE SKILLS TO DATABASE
        applicant.skills = skills 
        
        applicant.save()
        applicant.user.save()

        try:
            image = request.FILES['image']
            applicant.image = image
            applicant.save()
        except:
            pass
            
        alert = True
        return render(request, "user_homepage.html", {'alert': alert, 'applicant': applicant})
        
    return render(request, "user_homepage.html", {'applicant': applicant})

def all_jobs(request):
    # 1. Start with all jobs ordered by date
    jobs = Job.objects.all().order_by('-start_date')
    
    # 2. Get the search query from the URL (e.g., ?search=remote)
    query = request.GET.get('search', '') 

    # 3. If a query exists, filter the jobs
    if query:
        jobs = jobs.filter(
            Q(title__icontains=query) |           # Search in Title
            Q(location__icontains=query) |        # Search in Location
            Q(skills__icontains=query) |          # Search in Skills
            Q(company__company_name__icontains=query) # Search in Company Name
        )

    # 4. Existing logic for applied status
    try:
        applicant = Applicant.objects.get(user=request.user)
        apply = Application.objects.filter(applicant=applicant)
        data = [i.job.id for i in apply]
    except Applicant.DoesNotExist:
        data = []

    return render(request, "all_jobs.html", {
        'jobs': jobs,
        'data': data,
        'ai_result': None,
        'search_query': query  
    })

def job_detail(request, myid):
    job = Job.objects.get(id=myid)
    result = None

    if request.method == "POST":
        user_skills = request.POST.get("user_skills", "")
        
        # Logic to compare skills
        job_skills = [s.strip().lower() for s in job.skills.split(",")]
        user_skills_list = [s.strip().lower() for s in user_skills.split(",")]

        missing = [s for s in job_skills if s not in user_skills_list]

        suggestions = []
        projects = []

        for skill in missing:
            suggestions.append(f"Improve your knowledge in {skill}")
            if skill in ["java", "spring boot"]:
                projects.append("Build a REST API using Spring Boot")
            elif skill in ["sql", "mysql"]:
                projects.append("Design a database-backed application")
            elif skill in ["react", "javascript"]:
                projects.append("Create a frontend dashboard using React")
            elif skill in ["python", "django"]:
                projects.append("Build a Django CRUD project")
            else:
                projects.append(f"Create a mini project using {skill}")

        result = {
            "missing": missing,
            "suggestions": suggestions,
            "projects": list(set(projects))
        }

    return render(request, "job_detail.html", {"job": job, "result": result})

def job_apply(request, myid):
    if not request.user.is_authenticated:
        return redirect("/user_login")
    applicant = Applicant.objects.get(user=request.user)
    job = Job.objects.get(id=myid)
    date1 = date.today()
    if job.end_date < date1:
        closed=True
        return render(request, "job_apply.html", {'closed':closed})
    elif job.start_date > date1:
        notopen=True
        return render(request, "job_apply.html", {'notopen':notopen})
    else:
        if request.method == "POST":
            resume = request.FILES['resume']
            Application.objects.create(job=job, company=job.company, applicant=applicant, resume=resume, apply_date=date.today())
            alert=True
            return render(request, "job_apply.html", {'alert':alert})
    return render(request, "job_apply.html", {'job':job})

def all_applicants(request):
    company = Company.objects.get(user=request.user)
    application = Application.objects.filter(company=company)
    return render(request, "all_applicants.html", {'application':application})

def signup(request):
    next_param = request.GET.get('next', '/')
    if request.method == "POST":   
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        phone = request.POST.get('phone')
        gender = request.POST.get('gender')
        image = request.FILES.get('image')
        
        # 👇 CAPTURE SKILLS HERE TOO
        skills = request.POST.get('skills', '') 

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return redirect('/signup')
            
        try:
            # Create User
            user = User.objects.create_user(
                first_name=first_name, 
                last_name=last_name, 
                username=username, 
                password=password1,
                email=request.POST.get('email')
            )
            # Create Applicant with Skills
            Applicant.objects.create(
                user=user, 
                phone=phone, 
                gender=gender, 
                image=image, 
                type="applicant",
                skills=skills # 👈 Pass skills here
            )
            
            return redirect(f"/user_login/?next={next_param}")
            
        except Exception as e:
            messages.error(request, f"Error: {e}")
            return redirect('/signup')

    return render(request, "signup.html", {'next_param': next_param})

def company_signup(request):
    next_param = request.GET.get('next', '/')
    if request.method == "POST":
        try:
            email = request.POST['email']
            image = request.FILES['image']

            if not email or not image:
                raise ValidationError("Email or image not provided.")

            username = request.POST['username']
            first_name = request.POST['first_name']
            last_name = request.POST['last_name']
            password1 = request.POST['password1']
            password2 = request.POST['password2']
            phone = request.POST['phone']
            gender = request.POST['gender']
            company_name = request.POST['company_name']

            if password1 != password2:
                messages.error(request, "Passwords do not match.")
                return redirect('/company_signup')

            user = User.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                email=email,
                username=username,
                password=password1
            )
            company = Company.objects.create(
                user=user,
                phone=phone,
                gender=gender,
                image=image,
                company_name=company_name,
                type="company",
                status="pending"
            )
            user.save()
            company.save()
            return redirect(f"/company_login/?next={next_param}")

        except MultiValueDictKeyError as e:
            messages.error(request, "Error: Email or image not provided.")
            return redirect('/company_signup')

        except ValidationError as e:
            messages.error(request, f"Validation Error: {e}")
            return redirect('/company_signup')
        
    return render(request, "company_signup.html", {'next_param': next_param})

def company_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            try:
                company = Company.objects.get(user=user)
                if company.type == "company":
                    login(request, user)
                    messages.success(request, 'Login successful.')
                    return redirect("company_homepage")
                else:
                    messages.error(request, 'Invalid Company Type.')
            except Company.DoesNotExist:
                messages.error(request, 'Company profile not found.')
        else:
            messages.error(request, 'Invalid Credentials. Please try again.')

    return render(request, "company_login.html")

def company_homepage(request):
    if not request.user.is_authenticated:
        return redirect("/company_login")
    
    company = Company.objects.get(user=request.user)
    
    if request.method == "POST":   
        email = request.POST['email']
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        phone = request.POST['phone']
        gender = request.POST['gender']

        company.user.email = email
        company.user.first_name = first_name
        company.user.last_name = last_name
        company.phone = phone
        company.gender = gender
        company.save()
        company.user.save()

        try:
            image = request.FILES['image']
            company.image = image
            company.save()
        except:
            pass
        alert = True
        return render(request, "company_homepage.html", {'alert':alert, 'company':company})
    
    return render(request, "company_homepage.html", {'company':company})

def add_job(request):
    if not request.user.is_authenticated:
        return redirect("/company_login")
    if request.method == "POST":
        title = request.POST['job_title']
        start_date = request.POST['start_date']
        end_date = request.POST['end_date']
        salary = request.POST['salary']
        experience = request.POST['experience']
        location = request.POST['location']
        skills = request.POST['skills']
        description = request.POST['description']
        
        user = request.user
        company = Company.objects.get(user=user)
        
        job = Job.objects.create(
            company=company, 
            title=title,
            start_date=start_date, 
            end_date=end_date, 
            salary=salary, 
            image=company.image, 
            experience=experience, 
            location=location, 
            skills=skills, 
            description=description, 
            creation_date=date.today()
        )
        job.save()
        alert = True
        return render(request, "add_job.html", {'alert':alert})
    return render(request, "add_job.html")

def job_list(request):
    if not request.user.is_authenticated:
        return redirect("/company_login")
    
    # Ensure we only get THIS company's jobs
    company = Company.objects.get(user=request.user)
    jobs = Job.objects.filter(company=company)
    
    # Optional: Search within my own jobs
    query = request.GET.get('search')
    if query:
        jobs = jobs.filter(title__icontains=query)

    return render(request, "job_list.html", {'jobs':jobs})

def edit_job(request, myid):
    if not request.user.is_authenticated:
        return redirect("/company_login")
    job = Job.objects.get(id=myid)
    if request.method == "POST":
        title = request.POST['job_title']
        start_date = request.POST['start_date']
        end_date = request.POST['end_date']
        salary = request.POST['salary']
        experience = request.POST['experience']
        location = request.POST['location']
        skills = request.POST['skills']
        description = request.POST['description']

        job.title = title
        job.salary = salary
        job.experience = experience
        job.location = location
        job.skills = skills
        job.description = description

        job.save()
        if start_date:
            job.start_date = start_date
            job.save()
        if end_date:
            job.end_date = end_date
            job.save()
        alert = True
        return render(request, "edit_job.html", {'alert':alert})
    return render(request, "edit_job.html", {'job':job})

def company_logo(request, myid):
    if not request.user.is_authenticated:
        return redirect("/company_login")
    job = Job.objects.get(id=myid)
    if request.method == "POST":
        image = request.FILES['logo']
        job.image = image 
        job.save()
        alert = True
        return render(request, "company_logo.html", {'alert':alert})
    return render(request, "company_logo.html", {'job':job})

def Logout(request):
    logout(request)
    return redirect('/')

def admin_login(request):
    return redirect("/admin/")

def view_applicants(request):
    if not request.user.is_authenticated:
        return redirect("/admin_login")
    applicants = Applicant.objects.all()
    return render(request, "view_applicants.html", {'applicants':applicants})

def delete_applicant(request, myid):
    if not request.user.is_authenticated:
        return redirect("/admin_login")
    applicant = User.objects.filter(id=myid)
    applicant.delete()
    return redirect("/view_applicants")

def pending_companies(request):
    if not request.user.is_authenticated:
        return redirect("/admin_login")
    companies = Company.objects.filter(status="pending")
    return render(request, "pending_companies.html", {'companies':companies})

def change_status(request, myid):
    if not request.user.is_authenticated:
        return redirect("/admin_login")
    company = Company.objects.get(id=myid)
    if request.method == "POST":
        status = request.POST['status']
        company.status=status
        company.save()
        alert = True
        return render(request, "change_status.html", {'alert':alert})
    return render(request, "change_status.html", {'company':company})

def accepted_companies(request):
    if not request.user.is_authenticated:
        return redirect("/admin_login")
    companies = Company.objects.filter(status="Accepted")
    return render(request, "accepted_companies.html", {'companies':companies})

def rejected_companies(request):
    if not request.user.is_authenticated:
        return redirect("/admin_login")
    companies = Company.objects.filter(status="Rejected")
    return render(request, "rejected_companies.html", {'companies':companies})

def all_companies(request):
    if not request.user.is_authenticated:
        return redirect("/admin_login")
    companies = Company.objects.all()
    return render(request, "all_companies.html", {'companies':companies})

def delete_company(request, myid):
    if not request.user.is_authenticated:
        return redirect("/admin_login")
    company = User.objects.filter(id=myid)
    company.delete()
    return redirect("/all_companies")

def our_team(request):
    return render(request,"our_team.html")

def contact_us(request):
    return render(request,"contact_us.html")

def about_us(request):
    return render(request,"about_us.html")

# intern/views.py

import google.generativeai as genai
from pypdf import PdfReader
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import * # Import your Job model

# Configure Gemini (Replace with your actual key or load from env)
genai.configure(api_key="AIzaSyCPsL6pPPuAY2BiEXJWRMrzT_qCw77idDU")

def analyze_resume(request, job_id):
    if request.method == 'POST':
        try:
            # 1. Get the Job Description from your database
            job = get_object_or_404(Job, id=job_id) # Assuming your model is named 'Job'
            job_description = job.description # Adjust field name if yours is different

            # 2. Handle the Resume File
            uploaded_file = request.FILES.get('resume')
            if not uploaded_file:
                return JsonResponse({'error': 'No resume uploaded'}, status=400)

            # 3. Extract Text from PDF
            resume_text = ""
            try:
                reader = PdfReader(uploaded_file)
                for page in reader.pages:
                    resume_text += page.extract_text()
            except Exception as e:
                return JsonResponse({'error': 'Could not read PDF. Make sure it is text-based.'}, status=400)

            # 4. Construct the Prompt for AI
            prompt = f"""
            Act as a strict Application Tracking System (ATS) and Career Coach.
            
            Here is the Job Description:
            {job_description}
            
            Here is the Candidate's Resume:
            {resume_text}
            
            Please provide a detailed analysis in HTML format (use <ul>, <li>, <b> tags) with the following sections:
            1. <b>Match Score:</b> A percentage score out of 100.
            2. <b>Missing Skills:</b> List critical skills from the JD that are missing in the resume.
            3. <b>Profile Strengths:</b> What matches well.
            4. <b>Preparation Advice:</b> Specific topics to study to fill the gaps.
            
            Keep the tone encouraging but professional. Do not include ```html``` markdown code blocks, just return the raw HTML content.
            """

            # 5. Call Gemini API
            model = genai.GenerativeModel('gemini-flash-latest')
            response = model.generate_content(prompt)
            
            return JsonResponse({'analysis': response.text})

        except Exception as e:
            print(e)
            return JsonResponse({'error': 'Something went wrong during analysis'}, status=500)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)