from django import forms
from .models import TemporaryShp


class TemporaryShpForm(forms.ModelForm):
    shp_field = forms.FileField(widget=forms.ClearableFileInput(
        attrs={'multiple': True, 'class': 'form-control'}))

    class Meta:
        model = TemporaryShp
        exclude = ('shp_file_path',)

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        for field in self.fields:
            self.fields[ field ].widget.attrs[ 
                                        'onKeyUp' 
                                    ] = 'this.value=this.value.toUpperCase();'
            self.fields[ field ].widget.attrs[ 'class' ] = 'form-control'
            self.fields[ field ].widget.attrs[ 'placeholder' ] = self.fields[ field ].label

