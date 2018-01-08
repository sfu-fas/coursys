from django import forms
from django.forms import ModelForm
from django.conf import settings
from django.utils.safestring import mark_safe
import gzip, zipfile


class ComponentForm(ModelForm):
    title = forms.CharField(max_length=100, help_text='Name for this component (e.g. "Part 1" or "Programming Section")')
    specified_filename = forms.CharField(max_length=200, help_text="Specify the name of the file to be submitted.  Leave blank to accept any file name.", label="File name", required=False)


def filetype(fh):
    """
    Do some magic to guess the filetype.  Argument must be an open file-like object.
    """
    #TODO: would be nice to replace with some real checks
    fname = fh.name.lower()
    if fname.endswith('.doc') or fname.endswith('.docx'):
        return "MS-WORD"
    elif fname.endswith('.xls') or fname.endswith('.xlsx'):
        return "MS-EXCEL"
    elif fname.endswith('.ppt') or fname.endswith('.pptx'):
        return "MS-PPT"
    elif fname.endswith('.mpp'):
        return "MS-PROJ"
    elif fname.endswith('.vsd'):
        return "MS-VISIO"

    # methods extracted from the magic file (/usr/share/file/magic)
    # why not just check the filename?  Students seem to randomly rename.
    fh.seek(0)
    header = fh.read(10)
    magic = header[0:4]
    if magic == "PK\003\004" or magic == "PK00":
        # it's ZIP-ish: also look for ZIP-contained types
        fh.seek(0)
        try:
            zipf = zipfile.ZipFile(fh, "r")
            try:
                content_type = zipf.read("mimetype")
                if content_type == "application/vnd.oasis.opendocument.text":
                    return "OD-TEXT"
                elif content_type == "application/vnd.oasis.opendocument.presentation":
                    return "OD-PRES"
                elif content_type == "application/vnd.oasis.opendocument.spreadsheet":
                    return "OD-SS"
                elif content_type == "application/vnd.oasis.opendocument.graphics":
                    return "OD-GRA"
            except KeyError:
                pass

            return "ZIP"
        except (zipfile.BadZipfile, ValueError):
            pass

    elif magic == "Rar!":
        return "RAR"
    elif magic[0:2] == "\037\213":
        fh.seek(0)
        gzfh = gzip.GzipFile(filename="filename", fileobj=fh)
        try:
            gzfh.seek(257)
        except:
            # generic error occurs on invalid gzip data
            return None

        if gzfh.read(5) == "ustar":
            return "TGZ"
        else:
            return "GZIP"
    elif magic == "%PDF":
        return "PDF"
    elif magic in ["\377\330\377\340", "\377\330\377\356"]:
        return "JPEG"
    elif header[6:10] == "Exif" and magic[0:2] == "\377\330":
        return "JPEG"
    elif magic == "\211PNG":
        return "PNG"
    elif magic == "GIF8":
        return "GIF"

    fh.seek(257)
    if fh.read(5) == "ustar":
        return "TAR"

    return None


class SubmissionForm(ModelForm):
    # Set self.component to the corresponding Component object before doing validation.
    # e.g. "thisform.component = URLComponent.objects...."
    # This is automatically handled by make_form_from_list
    component = None

    class Meta:
        pass
        #model = a subclass of SubmittedComponent
        #fields = []
        #widgets = {}

    def check_size(self, upfile):
        """
        Check that file size is in allowed range.
        """
        if upfile.size / 1024 > self.component.max_size:
            return False
        return True

    def check_type(self, upfile):
        """
        Guess file type with magic, confirm that it matches file extension and is allowed for this submission type.
        """
        upfile.mode = "r" # not set in UploadedFile, so monkey-patch it in.
        ftype = filetype(upfile)

        # check that real file type is allowed
        allowed_types = self.instance.Type.Component.allowed_types
        if not ftype:
            raise forms.ValidationError('Unable to determine file type.  Allowed file types are: %s.' % (", ".join(list(allowed_types.keys()))))
        if ftype not in allowed_types:
            raise forms.ValidationError('Incorrect file type.  File contents appear to be %s.  Allowed file types are: %s.' % (ftype, ", ".join(list(allowed_types.keys()))))

        # check that extension matches
        extensions = allowed_types[ftype]
        if True not in [upfile.name.lower().endswith( e ) for e in extensions]:
            raise forms.ValidationError('File extension incorrect.  File appears to be %s data and is named "%s"; allowed extensions are: %s.' % (ftype, upfile.name, ", ".join(extensions)))

    def check_is_empty(self, data):
        if data == None:
            return True
        if len(data) == 0:
            return True
        return False

    def check_filename(self, data):
        # check if the submitted file matches specified file name
        specified_filename = self.component.specified_filename.strip()
        if specified_filename and len(specified_filename) > 0 and data.name != specified_filename:
            raise forms.ValidationError('File name incorrect.  This file is named "%s" but must be submitted with filename "%s".' % (data.name, specified_filename))

    def check_uploaded_data(self, data):
        if self.check_is_empty(data):
            raise forms.ValidationError("No file submitted.")
        self.check_type(data)
        self.check_filename(data)
        if not self.check_size(data):
            raise forms.ValidationError("File size exceeded max size, component can not be uploaded.")
        return data


def make_form_from_list(component_list, request=None):
    component_form_list = []
    for component in component_list:
        Type = component.Type
        if request:
            form = Type.SubmissionForm(request.POST, request.FILES, prefix=component.id)
        else:
            form = Type.SubmissionForm(prefix=component.id)
        form.component = component
        data = {'comp':component, 'form':form}
        component_form_list.append(data)
    return component_form_list

