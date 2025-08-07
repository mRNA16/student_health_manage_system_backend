from django.urls import path
from .views.AnalysisView import (
    analyze_health_data,
    get_analysis_results,
    get_analysis_detail,
    get_health_summary,
    delete_analysis_result
)

urlpatterns = [
    path('analyze/', analyze_health_data, name='analyze_health_data'),
    path('results/', get_analysis_results, name='get_analysis_results'),
    path('summary/', get_health_summary, name='get_health_summary'),
    path('results/<int:analysis_id>/', get_analysis_detail, name='get_analysis_detail'),
    path('results/<int:analysis_id>/delete/', delete_analysis_result, name='delete_analysis_result'),
] 