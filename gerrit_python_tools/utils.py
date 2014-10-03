import json
import cStringIO


class MultiJSON(object):
    """
    Class for parsing multiple JSON objects out of a single string.

    """
    def __init__(self, data):
        """
        Inits the MultiJSON object. Places the string into a cStringIO
        and reads one line at a time. json.loads is then executed on each
        line.

        @param data - String containing multiple json objects

        """
        buffer_ = cStringIO.StringIO(data)
        self.objects = [json.loads(line) for line in buffer_.readlines()]

    def __getitem__(self, index):
        """
        Returns the json object at index index.

        @param index - Integer index
        @return - JSON object

        """
        return self.objects[index]

    def __iter__(self):
        """
        Iterate over the objects

        @yields - Parsed json object.

        """
        for obj in self.objects:
            yield obj

    def __len__(self):
        """
        Return the number of json objects.

        @return - Integer

        """
        return len(self.objects)
