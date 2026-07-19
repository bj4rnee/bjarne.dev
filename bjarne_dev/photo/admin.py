from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path

from . import imaging
from .id_gen import generate_photo_id
from .models import Collection, Photograph

# metadata fields that EXIF may pre-fill, only when the admin left them blank
_META_FIELDS = ('camera', 'lens', 'focal_length', 'aperture',
                'shutter_speed', 'iso', 'capture_date')


def _apply_result(obj, result):
    obj.width = result['width']
    obj.height = result['height']
    obj.orientation = result['orientation']
    obj.version += 1
    for field in _META_FIELDS:
        value = result['metadata'].get(field)
        if value and not getattr(obj, field):
            setattr(obj, field, value)


def _speed_field():
    return forms.IntegerField(
        required=False, min_value=0, max_value=10,
        initial=settings.PHOTO_AVIF_SPEED,
        help_text='AVIF encode speed, 0 slowest/best to 10 fastest. '
                  'Blank uses the site default.')


class PhotographAdminForm(forms.ModelForm):
    image = forms.ImageField(
        required=False,
        help_text='Upload to generate the web images. On an existing photo, '
                  'leave empty to keep the current ones or pick a new file to '
                  'replace them.')
    avif_speed = _speed_field()

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


class BulkUploadForm(forms.Form):
    collection = forms.ModelChoiceField(queryset=Collection.objects.all())
    avif_speed = _speed_field()
    # files come from request.FILES.getlist('images'), the input is in the template


@admin.register(Photograph)
class PhotographAdmin(admin.ModelAdmin):
    form = PhotographAdminForm
    change_list_template = 'admin/photo/photograph_change_list.html'
    list_display = ('__str__', 'collection', 'orientation',
                    'capture_date', 'published', 'display_order')
    list_filter = ('collection', 'published', 'orientation')
    search_fields = ('title', 'camera', 'lens', 'location')
    readonly_fields = ('photo_id', 'width', 'height', 'orientation',
                       'version', 'upload_date')
    fieldsets = (
        (None, {'fields': ('image', 'avif_speed', 'collection', 'title',
                           'description', 'published', 'display_order')}),
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
            result = imaging.process_upload(
                upload, obj.photo_id, speed=form.cleaned_data.get('avif_speed'))
            _apply_result(obj, result)
        super().save_model(request, obj, form, change)

    def get_urls(self):
        custom = [path('bulk-upload/',
                       self.admin_site.admin_view(self.bulk_upload_view),
                       name='photo_photograph_bulk_upload')]
        return custom + super().get_urls()

    def bulk_upload_view(self, request):
        if request.method == 'POST':
            form = BulkUploadForm(request.POST)
            files = request.FILES.getlist('images')
            if form.is_valid() and files:
                collection = form.cleaned_data['collection']
                speed = form.cleaned_data.get('avif_speed')
                failed = []
                for f in files:
                    try:
                        obj = Photograph(collection=collection,
                                         photo_id=generate_photo_id())
                        _apply_result(obj, imaging.process_upload(
                            f, obj.photo_id, speed=speed))
                        obj.save()
                    except Exception:
                        failed.append(f.name)
                done = len(files) - len(failed)
                if done:
                    self.message_user(
                        request, f'Processed {done} photo(s) into {collection}.',
                        messages.SUCCESS)
                if failed:
                    self.message_user(
                        request, 'Skipped: ' + ', '.join(failed),
                        messages.WARNING)
                return redirect('admin:photo_photograph_changelist')
            if not files:
                form.add_error(None, 'Select at least one image.')
        else:
            form = BulkUploadForm()

        context = {
            **self.admin_site.each_context(request),
            'title': 'Bulk upload photos',
            'opts': self.model._meta,
            'form': form,
        }
        return render(request, 'admin/photo/bulk_upload.html', context)


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = ('name', 'slug', 'display_order', 'published_count')
