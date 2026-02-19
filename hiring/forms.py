from django import forms
from .models import HiringRequest

class HiringRequestForm(forms.ModelForm):
    class Meta:
        model = HiringRequest
        fields = ['work_profile', 'years_experience', 'difficulty_level', 
                 'number_of_questions_round1', 'number_of_questions_round2']
        widgets = {
            'work_profile': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Python Developer'}),
            'years_experience': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 50}),
            'difficulty_level': forms.Select(attrs={'class': 'form-control'}),
            'number_of_questions_round1': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 50}),
            'number_of_questions_round2': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 20}),
        }

class Round1AnswerForm(forms.Form):
    def __init__(self, *args, **kwargs):
        questions = kwargs.pop('questions', [])
        super().__init__(*args, **kwargs)
        
        for question in questions:
            if question.question_type == 'mcq':
                self.fields[f'question_{question.id}'] = forms.ChoiceField(
                    choices=[(i, option) for i, option in enumerate(question.options)],
                    widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
                    label=question.question_text
                )
            else:
                self.fields[f'question_{question.id}'] = forms.CharField(
                    widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                    label=question.question_text,
                    required=False
                )