import ipc
import numpy
from backend import Backend

def countLitPixels(image):
    hitscore = (image > Backend.state["aduThreshold"]).sum()
    return hitscore > Backend.state["hitscoreMinCount"], hitscore

def plotHitscore(hitscore):
    ipc.new_data("Hitscore", hitscore)
