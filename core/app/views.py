from django.shortcuts import render

# Create your views here.

def support_view(request):
    return render(request, 'support.html')

def about_view(request):
    return render(request, 'about.html')
