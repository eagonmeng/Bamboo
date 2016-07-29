from atom.api import Atom, Unicode, Bool, observe
from matplotlib.figure import Figure

class CurrentView(Atom):
    patient = Unicode()
    plot = Figure()

    @observe('yep')
    def update(self, change):

        s = templ.format(
            first=self.yep, last=self.nope,
        )
        print s

