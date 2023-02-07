"""
Code taken from:
https://gist.github.com/maedoc/b61090021d2a5161c5b9
"""

import numpy as np
import pyqtgraph as pg


class ColorBar(pg.GraphicsObject):
 
    def __init__(self, cmap, width, height, ticks=None, tick_labels=None, label=None):
        pg.GraphicsObject.__init__(self)
 
        # handle args
        label = label or ''
        w, h = width, height
        stops, colors = cmap.getStops('float')
        colors = (colors*255).astype(int)
        smn, spp = stops.min(), stops.ptp()
        stops = (stops - stops.min())/stops.ptp()
        if ticks is None:
            ticks = np.r_[0.0:1.0:5j, 1.0] * spp + smn
        tick_labels = tick_labels or ["%0.2g" % (t,) for t in ticks]
 
        # setup picture
        self.pic = pg.QtGui.QPicture()
        p = pg.QtGui.QPainter(self.pic)
 
        # draw bar with gradient following colormap
        p.setPen(pg.mkPen('k'))
        grad = pg.QtGui.QLinearGradient(w/2.0, 0.0, w/2.0, h*1.0)
        for stop, color in zip(stops, colors):
            grad.setColorAt(1.0 - stop, pg.QtGui.QColor(*[c for c in color]))
        p.setBrush(pg.QtGui.QBrush(grad))
        p.drawRect(pg.QtCore.QRectF(0, 0, w, h))
 
        # draw ticks & tick labels
        mintx = 0.0
        for tick, tick_label in zip(ticks, tick_labels):
            y_ = (1.0 - (tick - smn)/spp) * h
            p.drawLine(0, int(y_), -5, int(y_))
            br = p.boundingRect(0, 0, 0, 0, pg.QtCore.Qt.AlignRight, tick_label)
            if br.x() < mintx:
                mintx = br.x()
            p.drawText(br.x() - 10, int(y_) + br.height() // 4, tick_label)
 
        # draw label
        br = p.boundingRect(0, 0, 0, 0, pg.QtCore.Qt.AlignRight, label)
        p.drawText(-br.width() // 2, h + br.height() + 5, label)
        
        # done
        p.end()
 
        # compute rect bounds for underlying mask
        self.zone = mintx - 12, -15, br.width() - mintx, h + br.height() + 30
        
    def paint(self, p, *args):
        # paint underlying mask
        p.setPen(pg.QtGui.QColor(255, 255, 255, 0))
        p.setBrush(pg.QtGui.QColor(255, 255, 255, 100))
        p.drawRoundedRect(*(self.zone + (9, 9)))
        
        # paint colorbar
        p.drawPicture(0, 0, self.pic)
        
    def boundingRect(self):
        return pg.QtCore.QRectF(self.pic.boundingRect())
 
if __name__ == '__main__':
    app = pg.mkQApp()
 
    # use less ink
    pg.setConfigOption('background', 'w')
    pg.setConfigOption('foreground', 'k')
 
    pw = pg.plot()
    
    # make colormap
    stops = np.r_[-1.0, -0.5, 0.5, 1.0]
    colors = np.array([[0, 0, 1, 0.7], [0, 1, 0, 0.2], [0, 0, 0, 0.8], [1, 0, 0, 1.0]])
    cm = pg.ColorMap(stops, colors)
    
    # make colorbar, placing by hand
    cb = ColorBar(cm, 10, 200, label='Foo (Hz)')#, [0., 0.5, 1.0])
    pw.scene().addItem(cb)
    cb.translate(570.0, 90.0)
    
    # add data colored with colormap
    for x, y, z in np.random.randn(20, 3, 100):
        pw.plot(x, y, pen=None, symbol='o', symbolBrush=cm.map(z, 'qcolor'))
 
    app.exec_()
