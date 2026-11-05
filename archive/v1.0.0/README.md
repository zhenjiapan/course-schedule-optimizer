# Course Schedule Optimizer v1.0.0

Historical manual course-selection and hard-constraint validation application. This version does not provide the later preference-based recommendation search.

Run from this directory after installing `requirements.txt`:

```bash
python3 -m streamlit run app.py
```

Select one section per required course component, include at least one PED11-prefix course, and keep the total between 12 and 18 credits. The application checks missing selections and time conflicts, then renders a weekly timetable. Closed sections are listed with status labels; displayed schedules do not register courses in SIS.

`query_courses.py` provides read-only database queries, credit totals, pairwise section-conflict checks, and weekly timetable rows. `test_app.py` contains Streamlit AppTest scenarios. `check_timetable.py` checks timetable HTML structure; `_timetable_preview.html` is a generated reference preview.

The bundled database retains its historical schema and source data. Documentation and UI text have been translated to English, with original Chinese course names retained. Use the project-root application for the maintained v2.0.1 workflow.
