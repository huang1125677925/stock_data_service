from django.urls import path
from . import views

app_name = 'cctv_news'

urlpatterns = [
    path('', views.get_news_list, name='news_list'),
    path('<int:news_id>/', views.get_news_detail, name='news_detail'),
    path('create/', views.create_news, name='create_news'),
    path('<int:news_id>/update/', views.update_news, name='update_news'),
    path('<int:news_id>/delete/', views.delete_news, name='delete_news'),
    path('latest/', views.get_latest_news, name='latest_news'),
    path('search/', views.search_news, name='search_news'),
    path('wordcloud/', views.get_ai_content_wordcloud, name='ai_content_wordcloud'),
]