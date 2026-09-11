from django.contrib import admin
from django.urls import include, path

from apps.csc.views import CscView
from apps.schemes.views import (
    DeepCheckView,
    MatchView,
    MetaView,
    QuestionsView,
    QuickMatchView,
    SchemeDetailView,
    SchemesView,
    health,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health", health),
    path("", include("apps.accounts.urls")),
    path("meta", MetaView.as_view()),
    path("questions", QuestionsView.as_view()),
    path("schemes", SchemesView.as_view()),
    path("schemes/<str:scheme_id>", SchemeDetailView.as_view()),
    path("match", MatchView.as_view()),
    path("quick-match", QuickMatchView.as_view()),
    path("deep-check", DeepCheckView.as_view()),
    path("csc", CscView.as_view()),
]
