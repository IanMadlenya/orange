from OWBaseWidget import *
import os
import orange, orngTest #, orngStat
from copy import copy
from math import sqrt
import OWGUI, OWDlgs
import OWVisAttrSelection

CLASS_ACCURACY = 0
AVERAGE_CORRECT = 1
BRIER_SCORE = 2
ENTROPY_BASED = 3

LEAVE_ONE_OUT = 0
TEN_FOLD_CROSS_VALIDATION = 1
TEST_ON_LEARNING_SET = 2

ACCURACY = 0 
OTHER_RESULTS = 1
LEN_TABLE = 2
ATTR_LIST = 3
TRY_INDEX = 4
STR_LIST = 5

OTHER_ACCURACY = 0
OTHER_PREDICTIONS = 1
OTHER_DISTRIBUTION = 2

ALGORITHM_KNN = 0
ALGORITHM_HEURISTIC = 1

NUMBER_OF_INTERVALS = 6  # number of intervals to use when discretizing 

contMeasures = [("None", None), ("ReliefF", orange.MeasureAttribute_relief()), ("Fisher discriminant", OWVisAttrSelection.MeasureFisherDiscriminant())]
discMeasures = [("None", None), ("ReliefF", orange.MeasureAttribute_relief()), ("Gain ratio", orange.MeasureAttribute_gainRatio()), ("Gini index", orange.MeasureAttribute_gini())]

# array of testing methods. used by calling python's apply method depending on the value of self.testingMethod
testingMethods = [orngTest.leaveOneOut, orngTest.crossValidation, orngTest.learnAndTestOnLearnData]

class kNNOptimization(OWBaseWidget):
    EXACT_NUMBER_OF_ATTRS = 0
    MAXIMUM_NUMBER_OF_ATTRS = 1

    settingsList = ["kValue", "resultListLen", "percentDataUsed", "minExamples", "qualityMeasure", "testingMethod", "lastSaveDirName", "attrCont", "attrDisc", "showRank", "showAccuracy", "showInstances", "evaluationAlgorithm", "evaluateEachClassValue"]
    resultsListLenNums = [ 100 ,  250 ,  500 ,  1000 ,  5000 ,  10000, 20000, 50000, 100000, 500000 ]
    percentDataNums = [ 5 ,  10 ,  15 ,  20 ,  30 ,  40 ,  50 ,  60 ,  70 ,  80 ,  90 ,  100 ]
    kNeighboursNums = [ 0 ,  1 ,  2 ,  3 ,  4 ,  5 ,  6 ,  7 ,  8 ,  9 ,  10 ,  12 ,  15 ,  17 ,  20 ,  25 ,  30 ,  40 ,  60 ,  80 ,  100 ,  150 ,  200 ]
    resultsListLenList = [str(x) for x in resultsListLenNums]
    percentDataList = [str(x) for x in percentDataNums]
    kNeighboursList = [str(x) for x in kNeighboursNums]

    def __init__(self,parent=None, graph = None):
        OWBaseWidget.__init__(self, parent, "Optimization Dialog")

        self.setCaption("Qt VizRank Optimization Dialog")
        self.topLayout = QVBoxLayout( self, 10 ) 
        self.grid=QGridLayout(5,2)
        self.topLayout.addLayout( self.grid, 10 )

        self.graph = graph
        self.kValue = 10
        self.minExamples = 0
        self.resultListLen = 1000
        self.percentDataUsed = 100
        self.qualityMeasure = 1
        self.testingMethod = 1
        self.optimizationType = 0
        self.attributeCountIndex = 0
        self.evaluationAlgorithm = 0
        self.maxResultListLen = self.resultsListLenNums[len(self.resultsListLenNums)-1]
        self.onlyOnePerSubset = 1    # used in radviz and polyviz
        self.widgetDir = os.path.realpath(os.path.dirname(__file__)) + "/"
        self.parentName = "Projection"
        self.lastSaveDirName = os.getcwd() + "/"
        self.attrCont = 1
        self.attrDisc = 1
        #self.evaluateEachClassValue = 0
        self.dataDistribution = None    # distribution of class attribute
        self.selectedClasses = []
        self.rawdata = None

        self.showRank = 0
        self.showAccuracy = 1
        self.showInstances = 0
        self.allResults = []
        self.shownResults = []
        self.attrLenDict = {}
        self.datasetName = ""
        self.dataset = None
        self.cancelOptimization = 0

        self.loadSettings()

        self.tabs = QTabWidget(self, 'tabWidget')
        
        self.MainTab = QVGroupBox(self)
        self.SettingsTab = QVGroupBox(self)
        self.ManageTab = QVGroupBox(self)
        
        self.tabs.insertTab(self.MainTab, "Main")
        self.tabs.insertTab(self.SettingsTab, "Settings")
        self.tabs.insertTab(self.ManageTab, "Manage & Save")
        

        self.optimizationBox = OWGUI.widgetBox(self.MainTab, " Evaluate ")
        self.resultsBox = OWGUI.widgetBox(self.MainTab, " Projection List, Most Interesting First ")
        self.resultsDetailsBox = OWGUI.widgetBox(self.MainTab, " Shown Details in Projections List " , orientation = "horizontal")
        
        self.methodTypeCombo = OWGUI.comboBox(self.SettingsTab, self, "evaluationAlgorithm", box = "Projection evaluation method", tooltip = "Which learning method to use to use to evaluate given projections. \nk nearest neighbor or a very fast but not so perfect heuristic.", items = ["k-Nearest Neighbor", "Heuristic (very fast)"])
        self.optimizationSettingsBox = OWGUI.widgetBox(self.SettingsTab, " Optimization Settings for k-Nearest Neighbors")
        self.heuristicsSettingsBox = OWGUI.widgetBox(self.SettingsTab, " Heuristics for Attribute Ordering ")
        self.miscSettingsBox = OWGUI.widgetBox(self.SettingsTab, " Miscellaneous Settings ")
        #self.miscSettingsBox.hide()
        
        
        self.classesBox = OWGUI.widgetBox(self.ManageTab, " Class values in data set ")        
        self.manageResultsBox = OWGUI.widgetBox(self.ManageTab, " Manage Projections ")        
        self.evaluateBox = OWGUI.widgetBox(self.ManageTab, " Evaluate Current Projection / Classifier ")
        
        # ###########################
        # MAIN TAB
        self.buttonBox = OWGUI.widgetBox(self.optimizationBox, orientation = "horizontal")
        self.label1 = QLabel('Projections with ', self.buttonBox)
        self.optimizationTypeCombo = OWGUI.comboBox(self.buttonBox, self, "optimizationType", items = ["    exactly    ", "  maximum  "] )
        self.attributeCountCombo = OWGUI.comboBox(self.buttonBox, self, "attributeCountIndex", tooltip = "Evaluate only projections with exactly (or maximum) this number of attributes")
        self.attributeLabel = QLabel(' attributes', self.buttonBox)

        self.startOptimizationButton = OWGUI.button(self.optimizationBox, self, "Start evaluating projections")
        f = self.startOptimizationButton.font()
        f.setBold(1)
        self.startOptimizationButton.setFont(f)
        self.stopOptimizationButton = OWGUI.button(self.optimizationBox, self, "Stop evaluation", callback = self.stopOptimizationClick)
        self.stopOptimizationButton.setFont(f)
        self.stopOptimizationButton.hide()
        self.optimizeGivenProjectionButton = OWGUI.button(self.optimizationBox, self, "Optimize current projection")
        self.optimizeGivenProjectionButton.hide()

        for i in range(3,15):
            self.attributeCountCombo.insertItem(str(i))
        self.attributeCountCombo.insertItem("ALL")
        self.attributeCountIndex = 0

        self.resultList = QListBox(self.resultsBox)
        #self.resultList.setSelectionMode(QListBox.Extended)   # this would be nice if could be enabled, but it has a bug - currentItem doesn't return the correct value if this is on
        self.resultList.setMinimumSize(200,200)

        self.showRankCheck = OWGUI.checkBox(self.resultsDetailsBox, self, 'showRank', 'Rank', callback = self.updateShownProjections, tooltip = "Show projection ranks")
        self.showAccuracyCheck = OWGUI.checkBox(self.resultsDetailsBox, self, 'showAccuracy', 'Predicted Accuracy', callback = self.updateShownProjections, tooltip = "Show prediction accuracy of a k-NN classifier on the projection")
        self.showInstancesCheck = OWGUI.checkBox(self.resultsDetailsBox, self, 'showInstances', '# Instances', callback = self.updateShownProjections, tooltip = "Show number of instances in the projection")

        # ##########################
        # SETTINGS TAB
        self.attrKNeighboursCombo = OWGUI.comboBoxWithCaption(self.optimizationSettingsBox, self, "kValue", "Number of neighbors (k):                ", tooltip = "Number of neighbors used in k-NN algorithm to evaluate the projection", items = self.kNeighboursNums, sendSelectedValue = 1, valueType = int)
        self.percentDataUsedCombo= OWGUI.comboBoxWithCaption(self.optimizationSettingsBox, self, "percentDataUsed", "Percent of data used in evaluation: ", items = self.percentDataNums, sendSelectedValue = 1, valueType = int)

        self.measureCombo = OWGUI.comboBox(self.optimizationSettingsBox, self, "qualityMeasure", box = " Measure of Classification Success ", items = ["Classification accuracy", "Average probability assigned to the correct class", "Brier score"], tooltip = "Measure to evaluate prediction accuracy of k-NN method on the projected data set.")
        self.testingCombo = OWGUI.comboBox(self.optimizationSettingsBox, self, "testingMethod", box = " Testing Method ", items = ["Leave one out (slowest, most accurate)", "10 fold cross validation", "Test on learning set (fastest, least accurate)"], tooltip = "Method for evaluating the classifier. Slower are more accurate while faster give only a rough approximation.")

        #OWGUI.radioButtonsInBox(self.heuristicsSettingsBox, self, "attrCont", [val for (val, measure) in contMeasures], box = " Ordering of Continuous Attributes")
        #OWGUI.radioButtonsInBox(self.heuristicsSettingsBox, self, "attrDisc", [val for (val, measure) in discMeasures], box = " Ordering of Discrete Attributes")
        contHeuristic = OWGUI.widgetBox(self.heuristicsSettingsBox, " Ordering of Continuous Attributes", orientation = "vertical")
        OWGUI.comboBox(contHeuristic, self, "attrCont", items = [val for (val, m) in contMeasures])
        #OWGUI.checkBox(contHeuristic, self, "evaluateEachClassValue", "Evaluate attributes for each class value separately")
        OWGUI.comboBox(self.heuristicsSettingsBox, self, "attrDisc", box = " Ordering of Discrete Attributes", items = [val for (val, m) in discMeasures])

        self.resultListCombo = OWGUI.comboBoxWithCaption(self.miscSettingsBox, self, "resultListLen", "Maximum length of projection list:   ", tooltip = "Maximum length of the list of interesting projections. This is also the number of projections that will be saved if you click Save button.", items = self.resultsListLenNums, callback = self.updateShownProjections, sendSelectedValue = 1, valueType = int)
        self.minTableLenEdit = OWGUI.lineEdit(self.miscSettingsBox, self, "minExamples", "Minimum examples in data set:        ", orientation = "horizontal", tooltip = "Due to missing values, different subsets of attributes can have different number of examples. Projections with less than this number of examples will be ignored.", valueType = int)

        # ##########################
        # SAVE & MANAGE TAB

        self.classesCaption = QLabel('Select classes you wish to separate:', self.classesBox)
        self.classesList = QListBox(self.classesBox)
        self.classesList.setSelectionMode(QListBox.Multi)
        self.classesList.setMinimumSize(60,60)
        self.connect(self.classesList, SIGNAL("selectionChanged()"), self.classesListChanged)
        
        self.buttonBox3 = OWGUI.widgetBox(self.evaluateBox, orientation = "horizontal")
        self.evaluateProjectionButton = OWGUI.button(self.buttonBox3, self, 'Evaluate projection')
        #self.saveProjectionButton = OWGUI.button(self.buttonBox3, self, 'Save projection')
        self.saveBestButton = OWGUI.button(self.buttonBox3, self, "Save best graphs", self.exportMultipleGraphs)

        self.buttonBox4 = OWGUI.widgetBox(self.evaluateBox, orientation = "horizontal")
        self.showKNNCorrectButton = OWGUI.button(self.buttonBox4, self, 'kNN correct')
        self.showKNNWrongButton = OWGUI.button(self.buttonBox4, self, 'kNN wrong')
        self.showKNNResetButton = OWGUI.button(self.buttonBox4, self, 'Original') 
                
        self.attrLenCaption = QLabel('Number of concurrently visualized attributes:', self.manageResultsBox)
        self.attrLenList = QListBox(self.manageResultsBox)
        self.attrLenList.setSelectionMode(QListBox.Multi)
        self.attrLenList.setMinimumSize(60,60)
        self.connect(self.attrLenList, SIGNAL("selectionChanged()"), self.attrLenListChanged)

        self.reevaluateResults = OWGUI.button(self.manageResultsBox, self, "Reevaluate shown projections")
        #self.buttonBox5 = OWGUI.widgetBox(self.manageResultsBox, orientation = "horizontal")
        self.buttonBox6 = OWGUI.widgetBox(self.manageResultsBox, orientation = "horizontal")
        self.buttonBox7 = OWGUI.widgetBox(self.manageResultsBox, orientation = "horizontal")
        #self.removeSelectedButton = OWGUI.button(self.buttonBox5, self, "Remove selection", self.removeSelected)
        #self.filterButton = OWGUI.button(self.buttonBox5, self, "Save best graphs", self.exportMultipleGraphs)
        self.loadButton = OWGUI.button(self.buttonBox6, self, "Load", self.load)
        self.saveButton = OWGUI.button(self.buttonBox6, self, "Save", self.save)
        self.clearButton = OWGUI.button(self.buttonBox7, self, "Clear results", self.clearResults)
        self.closeButton = OWGUI.button(self.buttonBox7, self, "Close", self.hide)
        self.resize(350,550)
        self.setMinimumWidth(350)
        self.tabs.setMinimumWidth(350)

    # ##############################################################
    # EVENTS
    # ##############################################################
    
    # result list can contain projections with different number of attributes
    # user clicked in the listbox that shows possible number of attributes of result list
    # result list must be updated accordingly
    def attrLenListChanged(self):
        # check which attribute lengths do we want to show
        self.attrLenDict = {}
        for i in range(self.attrLenList.count()):
            intVal = int(str(self.attrLenList.text(i)))
            selected = self.attrLenList.isSelected(i)
            self.attrLenDict[intVal] = selected
        self.updateShownProjections()

    def classesListChanged(self):
        results = self.allResults
        self.clearResults()

        self.selectedClasses = self.getSelectedClassValues()
        if len(self.selectedClasses) in [self.classesList.count(), 0]:
            for result in results:
                self.addResult(result[OTHER_RESULTS][0], result[OTHER_RESULTS], result[LEN_TABLE], result[ATTR_LIST], result[TRY_INDEX], result[STR_LIST])
        else: 
            for result in results:
                acc = 0.0; sum = 0.0
                for index in self.selectedClasses:
                    acc += result[OTHER_RESULTS][OTHER_PREDICTIONS][index] * result[OTHER_RESULTS][OTHER_DISTRIBUTION][index]; sum += result[OTHER_RESULTS][OTHER_DISTRIBUTION][index]
                self.addResult(acc/sum, result[OTHER_RESULTS], result[LEN_TABLE], result[ATTR_LIST], result[TRY_INDEX], result[STR_LIST])
                
        self.finishedAddingResults()

    def clearResults(self):
        self.allResults = []
        self.shownResults = []
        self.resultList.clear()
        self.attrLenDict = {}
        self.attrLenList.clear()

    # remove projections that are selected
    def removeSelected(self):
        for i in range(self.resultList.count()-1, -1, -1):
            if self.resultList.isSelected(i):
                # remove from listbox and original list of results
                self.resultList.removeItem(i)
                self.shownResults.remove(self.shownResults[i])


    # ##############################################################
    # ##############################################################

    def getSelectedClassValues(self):
        selectedClasses = []
        for i in range(self.classesList.count()):
            if self.classesList.isSelected(i): selectedClasses.append(i)
        return selectedClasses


    def updateShownProjections(self, *args):
        self.resultList.clear()
        self.shownResults = []
        i = 0

        while self.resultList.count() < self.resultListLen and i < len(self.allResults):
            if self.attrLenDict[len(self.allResults[i][ATTR_LIST])] == 1:
                string = ""
                if self.showRank: string += str(i+1) + ". "
                if self.showAccuracy: string += "%.2f" % (self.allResults[i][ACCURACY])
                if not self.showInstances and self.showAccuracy: string += " : "
                elif self.showInstances: string += " (%d) : " % (self.allResults[i][LEN_TABLE])

                if self.allResults[i][STR_LIST] != "": string += self.allResults[i][STR_LIST]
                else: string += self.buildAttrString(self.allResults[i][ATTR_LIST])
                
                self.resultList.insertItem(string)
                self.shownResults.append(self.allResults[i])
            i+=1
        if self.resultList.count() > 0: self.resultList.setCurrentItem(0)        

    # set value of k to sqrt(n)
    def setData(self, data):
        if hasattr(data, "name"): self.datasetName = data.name
        else: self.datasetName = ""
        self.rawdata = data
        self.classesList.clear()
        self.selectedClasses = []

        if not data: return
        
        correct = sqrt(len(data))
        i=0
        # set value of k to square root of number of instances in dataset
        while i < len(self.kNeighboursNums) and self.kNeighboursNums[i] < correct: i+=1
        if i==0: self.kValue = self.kNeighboursNums[0]
        if i==len(self.kNeighboursNums): self.kValue = self.kNeighboursNums[-1]
        else: self.kValue = self.kNeighboursNums[i-1]

        if not (data.domain.classVar and data.domain.classVar.varType == orange.VarTypes.Discrete): return

        # add class values
        for i in range(len(data.domain.classVar.values)):
            self.classesList.insertItem(data.domain.classVar.values[i])
        self.classesList.selectAll(1)

        # compute class distribution for all data
        self.dataDistribution = orange.Distribution(data.domain.classVar, data)

                
    # given a dataset return a list of (val, attrName) where val is attribute "importance" and attrName is name of the attribute
    # class values that are not interesting for separation (indices not present in self.selectedClasses) are joined in one class value, so
    # that attributes are evaluated based on the interesting class values
    def getEvaluatedAttributes(self, data):
        selectedClassesStr = [data.domain.classVar.values[i] for i in self.selectedClasses]
        nonSelectedClassesStr = []
        for val in data.domain.classVar.values:
            if val not in selectedClassesStr: nonSelectedClassesStr.append(val)

        if len(nonSelectedClassesStr) > 0:
            selection = orange.EnumVariable("Selection", values = selectedClassesStr + ["nonSelectedClass"])

            shortData1 = data.select({data.domain.classVar.name: selectedClassesStr})
            shortData2 = data.select({data.domain.classVar.name: nonSelectedClassesStr})

            selection.getValueFrom = lambda ex, what: ex[data.domain.classVar]
            d1 = orange.Domain(shortData1.domain.attributes + [selection])
            data1 = orange.ExampleTable(d1, shortData1)

            selection.getValueFrom = lambda ex, what: orange.Value(selection, "nonSelectedClass")
            data2 = orange.ExampleTable(d1, shortData2)
            data1.extend(data2)
            data = data1
        
        """
        attrDict = {}
        if self.evaluateEachClassValue:
            for classVal in data.domain.classVar.values:
                if classVal == "nonSelectedClass": continue
                tempVar = orange.EnumVariable("OneClassVar", values = ["0","1"])
                tempVar.getValueFrom = lambda ex, foo: orange.Value(tempVar, str(int(ex[data.domain.classVar] == classVal)))
                tempData = orange.ExampleTable(orange.Domain(data.domain.attributes + [tempVar]), data)
                attrVals = OWVisAttrSelection.evaluateAttributes(tempData, contMeasures[self.attrCont][1], discMeasures[self.attrDisc][1])
                for (val, attr) in attrVals:
                    if attrDict.has_key(attr): attrDict[attr] += val
                    else: attrDict[attr] = val
            attributes = [(val, name) for (name, val) in attrDict.items()]
            attributes.sort()
            attributes.reverse()
            return attributes
        else:
            return OWVisAttrSelection.evaluateAttributes(data, contMeasures[self.attrCont][1], discMeasures[self.attrDisc][1])
        """
        return OWVisAttrSelection.evaluateAttributes(data, contMeasures[self.attrCont][1], discMeasures[self.attrDisc][1])

    
    def addResult(self, accuracy, other_results, lenTable, attrList, tryIndex, strList = ""):
        if self.getQualityMeasure() != BRIER_SCORE: funct = max
        else: funct = min
        self.insertItem(accuracy, other_results, lenTable, attrList, self.findTargetIndex(accuracy, funct), tryIndex, strList)
        qApp.processEvents()        # allow processing of other events

    # use bisection to find correct index
    def findTargetIndex(self, accuracy, funct):
        top = 0; bottom = len(self.allResults)

        while (bottom-top) > 1:
            mid  = (bottom + top)/2
            if funct(accuracy, self.allResults[mid][ACCURACY]) == accuracy: bottom = mid
            else: top = mid

        if len(self.allResults) == 0: return 0
        if funct(accuracy, self.allResults[top][ACCURACY]) == accuracy:
            return top
        else: 
            return bottom

    # insert new result - give parameters: accuracy of projection, number of examples in projection and list of attributes.
    # parameter strList can be a pre-formated string containing attribute list (used by polyviz)
    def insertItem(self, accuracy, other_results, lenTable, attrList, index, tryIndex, strList = ""):
        if index < self.maxResultListLen:
            self.allResults.insert(index, (accuracy, other_results, lenTable, attrList, tryIndex, strList))
        if index < self.resultListLen:
            string = ""
            if self.showRank: string += str(index+1) + ". "
            if self.showAccuracy: string += "%.2f" % (accuracy)
            if not self.showInstances and self.showAccuracy: string += " : "
            elif self.showInstances: string += " (%d) : " % (lenTable)

            if strList != "": string += strList
            else: string += self.buildAttrString(attrList)

            self.resultList.insertItem(string, index)
            self.shownResults.insert(index, (accuracy, lenTable, other_results, attrList, tryIndex, strList))

        # remove worst projection if list is too long
        if self.resultList.count() > self.resultListLen:
            self.resultList.removeItem(self.resultList.count()-1)
            self.shownResults.pop()
    
    def finishedAddingResults(self):
        self.cancelOptimization = 0
        
        self.attrLenList.clear()
        self.attrLenDict = {}
        maxLen = -1
        for i in range(len(self.shownResults)):
            if len(self.shownResults[i][ATTR_LIST]) > maxLen:
                maxLen = len(self.shownResults[i][ATTR_LIST])
        if maxLen == -1: return
        if maxLen == 2: vals = [2]
        else: vals = range(3, maxLen+1)
        for val in vals:
            self.attrLenList.insertItem(str(val))
            self.attrLenDict[val] = 1
        self.attrLenList.selectAll(1)
        self.resultList.setCurrentItem(0)

   
    # ##############################################################
    # ##############################################################
    # kNNEvaluate - evaluate class separation in the given projection
    # using a heuristic or k-NN method
    # ##############################################################
    # ##############################################################
    def kNNComputeAccuracy(self, table):
        # ###############################
        # select a subset of the data if necessary
        # ###############################
        percentDataUsed = int(str(self.percentDataUsedCombo.currentText()))
        if percentDataUsed != 100:
            indices = orange.MakeRandomIndices2(table, 1.0-float(percentDataUsed)/100.0)
            testTable = table.select(indices)
        else: testTable = table

        currentClassDistribution = orange.Distribution(testTable.domain.classVar, testTable)
        currentClassDistribution = [int(v) for v in currentClassDistribution]
        prediction = [0.0 for i in range(len(testTable.domain.classVar.values))]
        
        # ###############################
        # do we want to use very fast heuristic
        # ###############################
        if self.evaluationAlgorithm == ALGORITHM_HEURISTIC:
            # if input attributes are continuous (may be discrete for evaluating scatterplots, where we dicretize the whole domain...)
            if testTable.domain[0].varType == orange.VarTypes.Continuous and testTable.domain[1].varType == orange.VarTypes.Continuous:
                discX = orange.EquiDistDiscretization(testTable.domain[0], testTable, numberOfIntervals = NUMBER_OF_INTERVALS)
                discY = orange.EquiDistDiscretization(testTable.domain[0], testTable, numberOfIntervals = NUMBER_OF_INTERVALS)
                testTable = testTable.select([discX, discY, testTable.domain.classVar])

            # create a new attribute that is a cartesian product of the two visualized attributes
            nattr = orange.EnumVariable(values=['i' for i in range(NUMBER_OF_INTERVALS*NUMBER_OF_INTERVALS)])
            nattr.getValueFrom = orange.ClassifierByLookupTable2(nattr, testTable.domain[0], testTable.domain[1])
            for i in range(NUMBER_OF_INTERVALS*NUMBER_OF_INTERVALS): nattr.getValueFrom.lookupTable[i] = i
            
            for dist in orange.ContingencyAttrClass(nattr, testTable):
                dist = list(dist)
                if sum(dist) == 0: continue
                m = max(dist)
                prediction[dist.index(m)] += m * m / float(sum(dist))

            prediction = [val*100.0 for val in prediction]             # turn prediction array into percents
            acc = sum(prediction) / float(len(testTable))               # compute accuracy for all classes
            val = 0.0; s = 0.0
            for index in self.selectedClasses:                          # compute accuracy for selected classes
                val += prediction[index]; s += currentClassDistribution[index]
            for i in range(len(prediction)): prediction[i] /= float(currentClassDistribution[i])    # turn to probabilities
            return val/float(s), (acc, prediction, currentClassDistribution)
        
        # ###############################
        # or we want to use k nearest neighbor algorithm
        # ###############################
        knn = orange.kNNLearner(k=self.kValue, rankWeight = 0, distanceConstructor = orange.ExamplesDistanceConstructor_Euclidean(normalize=0))
        results = apply(testingMethods[self.testingMethod], [[knn], testTable])
        
        # compute classification success using selected measure
        if testTable.domain.classVar.varType == orange.VarTypes.Discrete:
            if self.qualityMeasure == AVERAGE_CORRECT:
                for res in results.results:
                    prediction[res.actualClass] += res.probabilities[0][res.actualClass]
                prediction = [val*100.0 for val in prediction]

            elif self.qualityMeasure == BRIER_SCORE:
                #return orngStat.BrierScore(results)[0], results
                for res in results.results:
                    val = 0
                    for prob in res.probabilities: val += prob*prob
                    val = val - 2*res.probabilities[res.actualClass] + 1
                    prediction[res.actualClass] += val
                
            elif self.qualityMeasure == CLASS_ACCURACY:
                #return 100*orngStat.CA(results)[0], results
                for res in results.results:
                    prediction[res.actualClass] += res.classes[0]==res.actualClass
                for i in range(len(prediction)): prediction[i] *= 100.0
                
            elif self.qualityMeasure == ENTROPY_BASED:
                # compute n/N * sum_i n_i/n * N_i/n_i * P_r_i = n/N * sum_i N_i/n * P_r_i
                pass

            # compute accuracy only for classes that are selected as interesting. other class values do not participate in projection evaluation
            acc = sum(prediction) / float(len(testTable))
            val = 0.0; s = 0.0
            for index in self.selectedClasses:
                val += prediction[index]; s += currentClassDistribution[index]
            for i in range(len(prediction)): prediction[i] /= float(currentClassDistribution[i])    # turn to probabilities

            return val/float(s), (acc, prediction, list(currentClassDistribution))
            
        # for continuous class we can't compute brier score and classification accuracy
        else:
            val = 0.0
            for res in results.results:  val += res.probabilities[0].density(res.actualClass)
            val/= float(len(results.results))
            return 100.0*val, (100.0*val)

        
    # ##############################################################
    # kNNClassifyData - compute classification error for every example in table
    def kNNClassifyData(self, table):
        qApp.processEvents()        # allow processing of other events
        
        knn = orange.kNNLearner(k=self.kValue, rankWeight = 0, distanceConstructor = orange.ExamplesDistanceConstructor_Euclidean(normalize=0))
        results = apply(testingMethods[self.testingMethod], [[knn], table])
            
        returnTable = []
        if table.domain.classVar.varType == orange.VarTypes.Discrete:
            lenClassValues = len(list(table.domain.classVar.values))
            if self.qualityMeasure == AVERAGE_CORRECT:
                for res in results.results:
                    returnTable.append(res.probabilities[0][res.actualClass])
            elif self.qualityMeasure == BRIER_SCORE:
                for res in results.results:
                    sum = 0
                    for val in res.probabilities[0]: sum += val*val
                    returnTable.append((sum + 1 - 2*res.probabilities[0][res.actualClass])/float(lenClassValues))
            elif self.qualityMeasure == CLASS_ACCURACY:
                for res in results.results:
                    returnTable.append(res.probabilities[0][res.actualClass] == max(res.probabilities[0]))
        else:
            # for continuous class we can't compute brier score and classification accuracy
            for res in results.results:
                returnTable.append(res.probabilities[0].density(res.actualClass))

        return returnTable

    """
    # TEST TEST TEST TEST !!!
    # from a given dataset return list of (acc, attrs), where attrs are subsets of lenght subsetSize of attributes from table
    # that give the best kNN prediction on table
    def kNNGetInterestingSubsets(self, subsetSize, attributes, returnListSize, table, testingList = []):
        if attributes == [] or subsetSize == 0:
            if len(testingList) != subsetSize: return []

            # do the testing
            self.currentSubset += 1
            attrs = []
            for attr in testingList:
                attrs.append(table.domain[attr])
            domain = orange.Domain(attrs + [table.domain.classVar])
            shortTable = orange.Preprocessor_dropMissing(table.select(domain))
            text = "Current attribute subset (%d/%d): " % (self.currentSubset, self.totalSubsets)
            for attr in testingList[:-1]: text += attr + ", "
            text += testingList[-1]
            if len(shortTable) < self.minExamples:
                print text + " - ignoring (too few examples)"
                return []
            print text
            return [(self.kNNComputeAccuracy(shortTable), testingList)]

        full1 = self.kNNGetInterestingSubsets(subsetSize, attributes[1:], returnListSize, table, testingList)
        testingList2 = copy(testingList)
        testingList2.insert(0, attributes[0])
        full2 = self.kNNGetInterestingSubsets(subsetSize, attributes[1:], returnListSize, table, testingList2)

        # find max values in booth lists
        full = full1 + full2
        shortList = []

        if table.domain.classVar.varType == orange.VarTypes.Discrete and self.qualityMeasure == CLASS_ACCURACY: funct = max
        else: funct = min
        for i in range(min(returnListSize, len(full))):
            item = funct(full)
            full.remove(item)
            shortList.append(item)

        return shortList
    """
    
    # ##############################################################
    # Loading and saving projection files
    # ##############################################################

    # save the list into a file - filename can be set if you want to call this function without showing the dialog
    def save(self, filename = None):
        if filename == None:
            # get file name
            if self.datasetName != "":
                filename = "%s - %s (k - %2d)" % (os.path.splitext(os.path.split(self.datasetName)[1])[0], self.parentName, self.kValue )
            else:
                filename = "%s (k - %2d)" % (self.parentName, self.kValue )
            qname = QFileDialog.getSaveFileName( self.lastSaveDirName + "/" + filename, "Interesting projections (*.proj)", self, "", "Save Projections")
            if qname.isEmpty(): return
            name = str(qname)
        else:
            name = filename

        # take care of extension
        if os.path.splitext(name)[1] != ".proj":
            name = name + ".proj"

        dirName, shortFileName = os.path.split(name)
        self.lastSaveDirName = dirName

        # open, write and save file
        file = open(name, "wt")
        attrs = ["kValue", "minExamples", "resultListLen", "percentDataUsed", "qualityMeasure", "testingMethod", "parentName", "evaluationAlgorithm"]
        dict = {}
        for attr in attrs:
            dict[attr] = self.__dict__[attr]
        file.write("%s\n" % (str(dict)))
        file.write("%s\n" % str(self.selectedClasses))
        for (acc, other_results, lenTable, attrList, tryIndex, strList) in self.shownResults:
            s = "(%.3f, (" % (acc)
            for val in other_results:
                if type(val) == float: s += "%.3f ," % val
                elif type(val) == list:
                    s += "["
                    for el in val:
                        if type(el) == float: s += "%.3f, " % (el)
                        elif type(el) == int: s += "%d, " % (el)
                        else: s += "%s, " % str(el)
                    if s[-2] == ",": s = s[:-2]
                    s += "], "
            if s[-2] == ",": s = s[:-2]
            s += "), %d, %s, %d, '%s')" % (lenTable, str(attrList), tryIndex, strList)
            file.write(s + "\n")
        file.flush()
        file.close()


    # load projections from a file
    def load(self):
        self.clearResults()
        if self.rawdata == None:
            QMessageBox.critical(None,'Load','There is no data. First load a data set and then load projection file',QMessageBox.Ok)
            return
                
        name = QFileDialog.getOpenFileName( self.lastSaveDirName, "Interesting projections (*.proj)", self, "", "Open Projections")
        if name.isEmpty(): return
        name = str(name)

        dirName, shortFileName = os.path.split(name)
        self.lastSaveDirName = dirName

        file = open(name, "rt")
        settings = eval(file.readline()[:-1])
        if settings.has_key("parentName") and settings["parentName"] != self.parentName:
            QMessageBox.critical( None, "Optimization Dialog", 'Unable to load projection file. It was saved for %s method'%(settings["parentName"]), QMessageBox.Ok)
            file.close()
            return

        self.setSettings(settings)

        # find if it was computed for specific class values
        ind = 0
        line = file.readline()[:-1];
        if type(eval(line)) == list:
            selectedClasses = eval(line)
            for i in range(len(self.rawdata.domain.classVar.values)):
                self.classesList.setSelected(i, i in selectedClasses)
            line = file.readline()[:-1]
        else:
            QMessageBox.critical(None,'Old version of projection file','This file was saved with an older version of Optimization Dialog. The new version of dialog offers \nsome additional functionality and therefore you have to compute the projection quality again.',QMessageBox.Ok)
            return
        
        while (line != ""):
            (acc, other_results, lenTable, attrList, tryIndex, strList) = eval(line)
            self.insertItem(acc, other_results, lenTable, attrList, ind, tryIndex, strList)
            line = file.readline()[:-1]
            ind+=1
        file.close()

        # update loaded results
        self.finishedAddingResults()


    # disable all controls while evaluating projections
    def disableControls(self):
        self.optimizationSettingsBox.setEnabled(0)
        #self.optimizationBox.setEnabled(0)
        self.optimizationTypeCombo.setEnabled(0)
        self.attributeCountCombo.setEnabled(0)
        #self.startOptimizationButton.setText(" Stop optimization ")
        self.startOptimizationButton.hide()
        self.stopOptimizationButton.show()
        self.manageResultsBox.setEnabled(0)
        self.evaluateBox.setEnabled(0)
        self.measureCombo.setEnabled(0)
        self.heuristicsSettingsBox.setEnabled(0)
        self.resultsDetailsBox.setEnabled(0)
        self.classesList.setEnabled(0)
        self.miscSettingsBox.setEnabled(0)
        self.methodTypeCombo.setEnabled(0)
        self.optimizeGivenProjectionButton.setEnabled(0)

    def enableControls(self):    
        self.optimizationSettingsBox.setEnabled(1)
        #self.optimizationBox.setEnabled(1)
        self.optimizationTypeCombo.setEnabled(1)
        self.attributeCountCombo.setEnabled(1)
        self.startOptimizationButton.show()
        self.stopOptimizationButton.hide()
        self.manageResultsBox.setEnabled(1)
        self.evaluateBox.setEnabled(1)
        self.measureCombo.setEnabled(1)
        self.heuristicsSettingsBox.setEnabled(1)
        self.resultsDetailsBox.setEnabled(1)
        self.classesList.setEnabled(1)
        self.miscSettingsBox.setEnabled(1)
        self.methodTypeCombo.setEnabled(1)
        self.optimizeGivenProjectionButton.setEnabled(1)

    # ##############################################################
    # exporting multiple pictures
    # ##############################################################
    def exportMultipleGraphs(self):
        (text, ok) = QInputDialog.getText('Qt Graph count', 'How many of the best projections do you wish to save?')
        if not ok: return
        self.bestGraphsCount = int(str(text))

        self.sizeDlg = OWDlgs.OWChooseImageSizeDlg(self.graph)
        self.sizeDlg.disconnect(self.sizeDlg.okButton, SIGNAL("clicked()"), self.sizeDlg.accept)
        self.sizeDlg.connect(self.sizeDlg.okButton, SIGNAL("clicked()"), self.saveToFileAccept)
        self.sizeDlg.exec_loop()

    def saveToFileAccept(self):
        fileName = str(QFileDialog.getSaveFileName("Graph","Portable Network Graphics (*.PNG);;Windows Bitmap (*.BMP);;Graphics Interchange Format (*.GIF)", None, "Save to..", "Save to.."))
        if fileName == "": return
        (fil,ext) = os.path.splitext(fileName)
        ext = ext.replace(".","")
        if ext == "":	
        	ext = "PNG"  	# if no format was specified, we choose png
        	fileName = fileName + ".png"
        ext = ext.upper()

        (fil, extension) = os.path.splitext(fileName)
        size = self.sizeDlg.getSize()
        for i in range(1, min(self.resultList.count(), self.bestGraphsCount+1)):
            self.resultList.setSelected(i-1, 1)
            self.graph.replot()
            name = fil + " (%02d)" % i + extension
            self.sizeDlg.saveToFileDirect(name, ext, size)
        QDialog.accept(self.sizeDlg)


    # ######################################################
    # Auxiliary functions
    # ######################################################

    # return a function that is appropriate to find the best projection in a list in respect to the selected quality measure
    def getMaxFunct(self):
        if self.rawdata.domain.classVar.varType == orange.VarTypes.Discrete and self.qualityMeasure != BRIER_SCORE: return max
        else: return min
    
    # from a list of attributes build a nice string with attribute names
    def buildAttrString(self, attrList):
        if len(attrList) == 0: return ""
        strList = attrList[0]
        for item in attrList[1:]:
            strList = strList + ", " + item
        return strList

    def getOptimizationType(self):
        return self.optimizationType

    def getQualityMeasure(self):
        return self.qualityMeasure

    def getQualityMeasureStr(self):
        if self.qualityMeasure ==0: return "Classification accuracy"
        elif self.qualityMeasure==1: return "Average probability of correct classification"
        else: return "Brier score"

    def getAllResults(self):
        return self.allResults

    def getShownResults(self):
        return self.shownResults

    def getSelectedProjection(self):
        if self.resultList.count() == 0: return None
        return self.shownResults[self.resultList.currentItem()]

    def resizeEvent(self, ev):
        self.tabs.resize(ev.size().width(), ev.size().height())

    def stopOptimizationClick(self):
        self.cancelOptimization = 1

    def isOptimizationCanceled(self):
        return self.cancelOptimization

    def destroy(self, dw, dsw):
        self.saveSettings()


#test widget appearance
if __name__=="__main__":
    import sys
    a=QApplication(sys.argv)
    ow=kNNOptimization()
    a.setMainWidget(ow)
    ow.show()
    a.exec_loop()        