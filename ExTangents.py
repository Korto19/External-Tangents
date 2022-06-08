# -*-coding: utf-8 -*-

"""
***************************************************************************
*                                                                         *
*   Korto19 06.06.2022                                                    *
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

from PyQt5.QtCore import QCoreApplication, QVariant
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsFeature,
                       QgsFeatureRequest,
                       QgsField,
                       QgsFields,
                       QgsGeometry,
                       QgsPoint,
                       QgsPointXY,
                       QgsWkbTypes,
                       QgsProject,
                       QgsVectorLayer,
                       QgsVectorLayerUtils,
                       QgsCoordinateReferenceSystem,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterEnum,
                       QgsProcessingParameterFile,
                       QgsProcessingParameterString,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterField,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterDefinition,
                       QgsProcessingFeatureSourceDefinition,
                       )
import processing
import datetime

#this code for processing icon
import os
import inspect
from qgis.PyQt.QtGui import QIcon
cmd_folder = os.path.split(inspect.getfile(inspect.currentframe()))[0]

class ExTangents_ProcessingAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm that fractions a poligon in n parts.
    """
    INPUTP = 'INPUTP'       #layer poligonale
    INPUTL = 'INPUTL'       #layer puntuale
    INPUTV = 'INPUTV'       #verso azimuth

    
    OUTPUT = 'OUTPUT'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return ExTangents_ProcessingAlgorithm()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'ExTangents'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('ExTangents')
        
    #processing icon
    def icon(self):
        cmd_folder = os.path.split(inspect.getfile(inspect.currentframe()))[0]
        icon = QIcon(os.path.join(os.path.join(cmd_folder, 'tan.svg')))
        return icon
        
    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr('')

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return ''

    def shortHelpString(self):
        """
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it..
        """
        header = '''
                    <img src="'''+ os.path.join(os.path.join(cmd_folder, 'tan.svg')) + '''" width="50" height="50" style="float:right">
        '''
        
        return self.tr(header + "<mark style='color:green'>Draws the tangents to a polygon passing through an external point.<p>\
        Make a new layer call 'T_line' with date and hour\
        <ul>Parameters:\
        <li>polygon layer</li>\
        <li>point layer</li>\
        <li>[opz] azimuth inverse</li>\
        </ul><br>\
        <mark style='color:red'>In some cases it is necessary to reverse the azimuth calculation to get the correct tangent<p>\
        <mark style='color:blue'>The created layer has two fields: azimuth and point to poligon id reference<p>\
        <mark style='color:black'><strong>If you have a multipolygon shape convert it before!")
        
    
    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """
        
        # We add the line input vector features source
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUTL,
                self.tr('Input Point layer'),
                [QgsProcessing.TypeVectorPoint],
                defaultValue = 'point'
            )
        )
        
        # We add the polygonal input vector features source
        #QgsProcessingFeatureSourceDefinition 
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUTP,
                self.tr('Input Polygon layer'),
                [QgsProcessing.TypeVectorPolygon],
                defaultValue = 'poly'
            )
        )

        
        #azimuth inverse
        INPUTV = QgsProcessingParameterBoolean(
            self.INPUTV,
            self.tr('Azimuth inverse'), 0
        )
        #INPUTV.setFlags(INPUTV.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(INPUTV)
        
        # We add a feature sink in which to store our processed features (this usually 
        # takes the form of a newly created vector layer when the algorithm is run in QGIS)
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('T_line_' + str((datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S"))))
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        p_layer = self.parameterAsSource(
            parameters,
            self.INPUTP,
            context)
        
        s_layer = self.parameterAsSource(
            parameters,
            self.INPUTL,
            context)
    
        a_versus = self.parameterAsBoolean(
            parameters,
            self.INPUTV,
            context)
        
        
        fields = QgsFields()
        fields.append(QgsField('azimuth', QVariant.Double))
        fields.append(QgsField('set', QVariant.String))

        
        (t_line, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context, fields, QgsWkbTypes.LineString, p_layer.sourceCrs() #QgsCoordinateReferenceSystem('EPSG:32632') )
        )
        
        def trace_tangent_line(star, item_id):
            #trace tangent line to polygon from star
            for item in p_layer.getFeatures():
                azimuths = []
                
                #get polygon vertex number and calculate azimuth
                polygon = item.geometry().asPolygon()
                n = len(polygon[0])
                for i in range(n):
                    if not a_versus:
                        azimuths.append((QgsPointXY(polygon[0][i].x(),polygon[0][i].y())).azimuth(QgsPointXY(star.x(),star.y())))
                    else:
                        azimuths.append((QgsPointXY(star.x(),star.y()).azimuth(QgsPointXY(polygon[0][i].x(),polygon[0][i].y()))))
                #print(azimuths)
                
                #get polygon vertex number and meke tangent line
                polygon = item.geometry().asPolygon()
                n = len(polygon[0])
                
                first_time_min = 0
                first_time_max = 0
                
                for i in range(n):

                    seg = QgsFeature(fields)
                    seg.setGeometry(QgsGeometry.fromPolyline([QgsPoint(star.x(),star.y()), QgsPoint(polygon[0][i].x(),polygon[0][i].y())]))
                    
                    #get segment azimuth
                    if not a_versus:
                        seg_azimuth = (QgsPointXY(polygon[0][i].x(),polygon[0][i].y())).azimuth(QgsPointXY(star.x(),star.y()))
                    else:
                        seg_azimuth = (QgsPointXY(star.x(),star.y()).azimuth(QgsPointXY(polygon[0][i].x(),polygon[0][i].y())))
        
                    if seg_azimuth == max(azimuths) and first_time_max == 0:
                        seg.setAttributes([seg_azimuth, str(item_id) +'_'+ str(item.id())])
                        t_line.addFeature(seg, QgsFeatureSink.FastInsert)
                        first_time_max = 1
                        
                    if seg_azimuth == min(azimuths) and first_time_min == 0:
                        seg.setAttributes([seg_azimuth, str(item_id) +'_'+ str(item.id())])
                        t_line.addFeature(seg, QgsFeatureSink.FastInsert)
                        first_time_min = 1
                        
        for item in s_layer.getFeatures():
            geometry = item.geometry()
            star = geometry.asPoint()
            trace_tangent_line(star, item.id())

                
        return {self.OUTPUT: dest_id}
