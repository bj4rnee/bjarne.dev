from django import forms
from django.contrib import admin

from . import imaging
from .id_gen import generate_photo_id
from .models import Collection, Photograph

# metadata fields that EXIF may pre-fill, only when the admin left them blank
_META_FIELDS = ('camera', 'lens', 'focal_length', 'aperture',
                'shutter_speed', 'iso', 'capture_date')


class PhotographAdminForm(forms.ModelForm):
    image = forms.ImageField(
        required=False,
        help_text='Upload to generate the web images. On an existing photo, '
                  'leave empty to keep the current ones or pick a new file to '
                  'replace them.')

    class Meta:
        model = Photograph
        fields = ('collection', 'title', 'description', 'published',
                  'display_order', 'camera', 'lens', 'focal_length',
                  'aperture', 'shutter_speed', 'iso', 'location',
                  'capture_date')

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if not self.instance.pk and not image:
            raise forms.ValidationError('An image file is required.')
        return image


@admin.register(Photograph)
class PhotographAdmin(admin.ModelAdmin):
    form = PhotographAdminForm
    list_display = ('__str__', 'collection', 'orientation',
                    'capture_date', 'published', 'display_order')
    list_filter = ('collection', 'published', 'orientation')
    search_fields = ('title', 'camera', 'lens', 'location')
    readonly_fields = ('photo_id', 'width', 'height', 'orientation',
                       'version', 'upload_date')
    fieldsets = (
        (None, {'fields': ('image', 'collection', 'title', 'description',
                           'published', 'display_order')}),
        ('Capture metadata', {'fields': (
            'capture_date', 'camera', 'lens', 'focal_length', 'aperture',
            'shutter_speed', 'iso', 'location')}),
        ('Generated', {'fields': (
            'photo_id', 'width', 'height', 'orientation', 'version',
            'upload_date')}),
    )

    def save_model(self, request, obj, form, change):
        upload = form.cleaned_data.get('image')
        if upload:
            if not obj.photo_id:
                obj.photo_id = generate_photo_id()
            result = imaging.process_upload(upload, obj.photo_id)
            obj.width = result['width']
            obj.height = result['height']
            obj.orientation = result['orientation']
            obj.version += 1
            for field in _META_FIELDS:
                value = result['metadata'].get(field)
                if value and not getattr(obj, field):
                    setattr(obj, field, value)
        super().save_model(request, obj, form, change)


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = ('name', 'slug', 'display_order', 'published_count')
