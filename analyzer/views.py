import pandas as pd
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import seaborn as sns
import os

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score

from .models import UploadedFile


@login_required
def dashboard(request):
    REQUIRED_COLUMNS = ['Name', 'Maths', 'Science', 'English', 'Computer', 'History']

    # ---------------- FILE UPLOAD ----------------
    if request.method == 'POST' and request.FILES.get('file'):
        UploadedFile.objects.filter(user=request.user).update(is_active=False)

        UploadedFile.objects.create(
            user=request.user,
            file=request.FILES['file'],
            is_active=True
        )

        return redirect('/')

    # ---------------- GET ACTIVE FILE ----------------
    latest_file = UploadedFile.objects.filter(user=request.user, is_active=True).first()
    file_path = latest_file.file.path if latest_file else 'data.csv'

    # ---------------- READ CSV ----------------
    try:
        data = pd.read_csv(file_path)
    except:
        return render(request, 'dashboard.html', {'error': '❌ Failed to read CSV file'})

    data.columns = data.columns.str.strip()

    if not all(col in data.columns for col in REQUIRED_COLUMNS):
        if latest_file:
            latest_file.delete()
        return render(request, 'dashboard.html', {
            'error': f'❌ Invalid CSV! Required columns: {", ".join(REQUIRED_COLUMNS)}'
        })

    subjects = ['Maths', 'Science', 'English', 'Computer', 'History']

    # ---------------- PROCESSING ----------------
    data['Total'] = data[subjects].sum(axis=1)
    data['Average'] = data[subjects].mean(axis=1)

    def assign_grade(avg):
        if avg >= 90: return 'A'
        elif avg >= 75: return 'B'
        elif avg >= 60: return 'C'
        else: return 'D'

    data['Grade'] = data['Average'].apply(assign_grade)

    top_student = data.loc[data['Average'].idxmax()]
    top_5 = data.sort_values(by='Average', ascending=False).head(5)
    subject_avg = data[subjects].mean()

    # ---------------- ML ----------------
    X = data[['Maths', 'Science', 'Computer']]
    y = data['English']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

    model = LinearRegression()
    model.fit(X_train, y_train)

    accuracy = r2_score(y_test, model.predict(X_test))

    data['Predicted_English'] = model.predict(X)

    data['Predicted_Average'] = (
        data['Maths'] + data['Science'] + data['Computer'] + data['Predicted_English'] + data['History']
    ) / 5

    predicted_topper = data.loc[data['Predicted_Average'].idxmax()]

    # ---------------- CHARTS ----------------
    static_path = os.path.join('analyzer', 'static')

    plt.figure()
    sns.barplot(x=subject_avg.index, y=subject_avg.values)
    plt.savefig(os.path.join(static_path, 'bar_chart.png'))
    plt.close()

    plt.figure()
    data['Grade'].value_counts().plot(kind='pie', autopct='%1.1f%%')
    plt.savefig(os.path.join(static_path, 'pie_chart.png'))
    plt.close()

    plt.figure()
    plt.hist(data['Average'], bins=5)
    plt.savefig(os.path.join(static_path, 'hist_chart.png'))
    plt.close()

    # ---------------- COMPARE ----------------
    files = UploadedFile.objects.filter(user=request.user).order_by('-uploaded_at')
    compare_data = None

    if 'compare' in request.GET:
        try:
            if len(files) < 2:
                raise Exception("Need at least 2 files")

            file1_id = request.GET.get('file1')
            file2_id = request.GET.get('file2')

            file1 = UploadedFile.objects.get(id=file1_id) if file1_id else files[0]
            file2 = UploadedFile.objects.get(id=file2_id) if file2_id else files[1]

            if file1.id == file2.id:
                raise Exception("Select two different files")

            df1 = pd.read_csv(file1.file.path)
            df2 = pd.read_csv(file2.file.path)

            avg1 = df1[subjects].mean()
            avg2 = df2[subjects].mean()

            difference = (avg2 - avg1).to_dict()

            plt.figure()
            x = range(len(subjects))
            plt.bar(x, avg1.values, width=0.4, label='File 1')
            plt.bar([i + 0.4 for i in x], avg2.values, width=0.4, label='File 2')
            plt.xticks([i + 0.2 for i in x], subjects)
            plt.legend()
            plt.title("Dataset Comparison")

            plt.savefig(os.path.join(static_path, 'compare_chart.png'))
            plt.close()

            compare_data = {
                'chart': 'compare_chart.png',
                'difference': difference
            }

        except Exception as e:
            compare_data = {'error': f'❌ {str(e)}'}

    context = {
        'students': data.to_dict(orient='records'),
        'top_student': top_student.to_dict(),
        'top_5': top_5.to_dict(orient='records'),
        'subject_avg': subject_avg.to_dict(),
        'predicted_topper': predicted_topper.to_dict(),
        'accuracy': round(accuracy, 2),
        'bar_chart': 'bar_chart.png',
        'pie_chart': 'pie_chart.png',
        'hist_chart': 'hist_chart.png',
        'last_file': latest_file.file.name if latest_file else "Default data.csv",
        'files': files,
        'compare_data': compare_data
    }

    return render(request, 'dashboard.html', context)


def reset_data(request):
    UploadedFile.objects.all().delete()
    return redirect('/')


def delete_file(request, file_id):
    file = get_object_or_404(UploadedFile, id=file_id)
    file.delete()
    return redirect('/')

def set_active(request, file_id):
    UploadedFile.objects.filter(user=request.user).update(is_active=False)

    file = UploadedFile.objects.get(id=file_id, user=request.user)
    file.is_active = True
    file.save()

    return redirect('/')