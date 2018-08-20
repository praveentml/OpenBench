from django.urls import path

import OpenBench.views

urlpatterns = [
    path(r'register/', OpenBench.views.register),
    path(r'login/', OpenBench.views.login),
    path(r'logout/', OpenBench.views.logout),

    path(r'viewProfile/', OpenBench.views.viewProfile),
    path(r'editProfile/', OpenBench.views.editProfile),

    path(r'index/', OpenBench.views.index),
    path(r'index/<int:page>/', OpenBench.views.index),
    path(r'greens/', OpenBench.views.greens),
    path(r'greens/<int:page>/', OpenBench.views.greens),
    path(r'search/', OpenBench.views.search),
    path(r'viewUser/<str:username>/', OpenBench.views.viewUser),
    path(r'viewUser/<str:username>/<int:page>/', OpenBench.views.viewUser),

    path(r'users/', OpenBench.views.users),
    path(r'machines/', OpenBench.views.machines),
    path(r'eventLog/', OpenBench.views.eventLog),
    path(r'eventLog/<int:page>/', OpenBench.views.eventLog),

    path(r'newTest/', OpenBench.views.newTest),
    path(r'viewTest/<int:id>/', OpenBench.views.viewTest),
    path(r'editTest/<int:id>/', OpenBench.views.editTest),
    path(r'approveTest/<int:id>/', OpenBench.views.approveTest),
    path(r'restartTest/<int:id>/', OpenBench.views.restartTest),
    path(r'stopTest/<int:id>/', OpenBench.views.stopTest),
    path(r'deleteTest/<int:id>/', OpenBench.views.deleteTest),

    path(r'getFiles/', OpenBench.views.getFiles),
    path(r'getWorkload/', OpenBench.views.getWorkload),
    path(r'wrongBench/', OpenBench.views.wrongBench),
    path(r'submitNPS/', OpenBench.views.submitNPS),
    path(r'submitResults/', OpenBench.views.submitResults),

    path(r'', OpenBench.views.index),
]
