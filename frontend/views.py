import os
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.cache import never_cache

@never_cache
def home_view(request):
    if not request.user.is_authenticated:
        return redirect('frontend:login')
    if not request.user.is_active:
        logout(request)
        return redirect('/login/?deactivated=true')
    return render(request, 'index.html', {'user': request.user})

@never_cache
def login_view(request):
    if request.GET.get('logout') == 'true':
        logout(request)
    elif request.user.is_authenticated and request.user.is_active:
        return redirect('frontend:home')
    deactivated = request.GET.get('deactivated') == 'true'
    return render(request, 'login.html', {'deactivated': deactivated})

@never_cache
def logout_view(request):
    logout(request)
    response = redirect('/login/')
    response.delete_cookie(settings.SESSION_COOKIE_NAME, path='/')
    response.delete_cookie('csrftoken', path='/')
    return response

@never_cache
def register_view(request):
    if request.user.is_authenticated and request.user.is_active:
        return redirect('frontend:home')
    return render(request, 'register.html')

def manifest_view(request):
    manifest_path = os.path.join(settings.BASE_DIR, 'frontend', 'static', 'manifest.json')
    if os.path.exists(manifest_path):
        with open(manifest_path, 'rb') as f:
            return HttpResponse(f.read(), content_type='application/manifest+json')
    return HttpResponse('{}', content_type='application/manifest+json')

def service_worker_view(request):
    sw_path = os.path.join(settings.BASE_DIR, 'frontend', 'static', 'sw.js')
    if os.path.exists(sw_path):
        with open(sw_path, 'rb') as f:
            resp = HttpResponse(f.read(), content_type='application/javascript')
            resp['Service-Worker-Allowed'] = '/'
            return resp
    return HttpResponse('', content_type='application/javascript')

def offline_view(request):
    return render(request, 'offline.html')

def robots_txt_view(request):
    return HttpResponse("User-agent: *\nDisallow: /\n", content_type="text/plain")


