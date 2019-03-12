from .image import ImagePad
from ipywidgets import Checkbox, Select, Text
import re

class DataWrapper:

    anonindex = 1

    def __init__(self, *args, **kwargs):

        if 'name' in kwargs:
            self.name = kwargs['name']
        else:
            self.name = 'data{}'.format(DataWrapper.anonindex)
            DataWrapper.anonindex += 1

        self.desc = kwargs.get('desc', self.name)

        if len(args) > 0:
            self.data = args[0]
            if 'data' in kwargs:
                raise Exception('data supplied both as position and keyword argument')
        elif 'data' in kwargs:
            self.data = kwargs['data']
        else:
            raise Exception('No data argument found')

        self.widget = None

    def get_name(self):
        return self.name

    def post_register(self, datamanager):
        pass

    def post_widget_create(self, datamanager):
        pass

    def __len__(self):
        return len(self.data)

    def get_widget(self):
        if self.widget is None:
            self.widget = self._create_widget() # on derived class
        return self.widget

    def update_ui(self, index):
        raise Exception('Do not call update_ui on base class')

    def update_data(self, index):
        raise Exception('Do not call update_data on an input-only class')


class ImageDataWrapper(DataWrapper):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.width = kwargs.get('width', '')
        self.height = kwargs.get('height', '')

    def _create_widget(self):
        return ImagePad(width=self.width, height=self.height)

    def update_ui(self, index):
        if hasattr(self.data[index], '__fspath__') or isinstance(self.data[index], str):
            # Path-like
            self.get_widget().set_value_from_file(self.data[index])
        elif 'numpy' in str(type(self.data[index])):
            import cv2

            self.get_widget().value = cv2.imencode('.png', self.data[index])[1].tostring()
        else:
            # Actual raw image data
            self.get_widget().value = self.data[index]

    def setRect(self, x,y,w,h):
        self.get_widget().setRect(x,y,w,h)


class BoundingBoxDataWrapper(DataWrapper):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.source = kwargs.get('source', None)
        self.sourcedw = None

    def post_register(self, datamanager):
        if self.source is not None:
            self.sourcedw = datamanager.get_data_wrapper_by_name(self.source)

            if self.sourcedw is None:
                raise Exception(f'ImageDataWrapper named {self.source} not found but specified as source attribute for BoundingBoxDataWrapper')

        else:
            # Find by type
            dws = datamanager.get_data_wrappers_by_type(ImageDataWrapper)
            if len(dws) != 1:
                # Raises exception if 0 or >1 of these is found
                raise Exception(f'ImageDataWrapper not found uniquely')

            self.sourcedw = dws[0]

        super().post_register(datamanager)

    def post_widget_create(self, datamanager):
        if self.sourcedw is not None:
            self.sourcedw.get_widget().observe(self.rectChanged, names='rect')

    def _create_widget(self):
        return Text()

    def update_ui(self, index):
        self.get_widget().value = self._value_to_str(self.data[index])
        self._sync_to_image(index)

    def _sync_to_image(self, index):
        if self.sourcedw is not None:
            (x,y,w,h) = self.data[index][:4]
            self.sourcedw.setRect(x,y,w,h)

    def _value_to_str(self, r):
        return ', '.join([str(a) for a in r])

    def update_data(self, index):
        newval = self.get_widget().value
        if newval != self._value_to_str(self.data[index]):
            try:
                self.data[index] = [int(s) for s in re.split('[ ,]+', newval)]
                self._sync_to_image(index)
            except ValueError:
                pass

    def rectChanged(self, change):
        if self.sourcedw is not None:
            r = self.sourcedw.get_widget().rect
            self.get_widget().value = self._value_to_str(r)


class BinaryClassificationDataWrapper(DataWrapper):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        if 'classes' in kwargs:
            self.classes = kwargs['classes']
        else:
            self.classes = ['False', 'True']

    def _create_widget(self):
        return Checkbox(description=self.desc)

    def update_ui(self, index):
        self.get_widget().value = self.data[index] == 1

    def update_data(self, index):
        newval = self.get_widget().value and 1 or 0
        if newval != self.data[index]:
            self.data[index] = newval


class MultiClassificationDataWrapper(DataWrapper):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        if 'classes' in kwargs:
            self.classes = kwargs['classes']
        else:
            self.classes = [str(i) for i in range(5)] # TODO Calc from data

    def _create_widget(self):
        return Select(options=self.classes)

    def update_ui(self, index):
        self.get_widget().value = self.classes[self.data[index]]

    def update_data(self, index):
        newval = self.get_widget().value
        if newval != self.classes[self.data[index]]:
            self.data[index] = self.classes.index(newval)