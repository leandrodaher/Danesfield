import argparse
import gdal
from danesfield import gdal_utils
from danesfield import gen_kw18
import logging
import ogr
import os
import osr
import pyproj

def main(args):
    global VECTOR_TYPES
    parser = argparse.ArgumentParser(
        description='Convert polygons into WAMI-Viewer kw18 format. A polygon is '
                    'a list of points pixel value coordinates. ')
    parser.add_argument('input_vector',
                        help='Buildings vector file with OSM or US Cities data.')
    parser.add_argument('input_image', help='Image from which to read the resolution '
                        'and the geo position of the data. '
                        'Assume image has square pixels aligned with XY axes. '
                        'The vector and image cover the same area '
                        '(as generated by align-buildings.py)')
    parser.add_argument('output_base',
                        help='Output base for files in WAMI-Viewer kw18 format')
    parser.add_argument('--debug', action='store_true',
                        help='Print debugging information')
    args = parser.parse_args(args)

    inputImage = gdal_utils.gdal_open(args.input_image, gdal.GA_ReadOnly)
    # get imageProj
    projection = inputImage.GetProjection()
    if not projection:
        projection = raster.GetGCPProjection()
    imageSrs = osr.SpatialReference(wkt=projection)
    imageProj = pyproj.Proj(imageSrs.ExportToProj4())

    # BB in image geo coordinates
    [minX, minY, maxX, maxY] = gdal_utils.gdal_bounding_box(inputImage)
    pixelSizeX = (maxX - minX) / inputImage.RasterXSize
    pixelSizeY = (maxY - minY) / inputImage.RasterYSize
    print("Image size ({},{}), BB({}, {}, {}, {}), pixel size ({}, {})".format(
        inputImage.RasterXSize, inputImage.RasterYSize,
        minX, maxX, minY, maxY,
        pixelSizeX, pixelSizeY))

    inputVector = gdal_utils.ogr_open(args.input_vector)
    inputLayer = gdal_utils.ogr_get_layer(inputVector, ogr.wkbPolygon)
    vectorSrs = inputLayer.GetSpatialRef()
    vectorProj = pyproj.Proj(vectorSrs.ExportToProj4())
    inputFeatures = list(inputLayer)

    polygonId = 0
    polygons = {}
    for feature in inputFeatures:
        points = []
        poly = feature.GetGeometryRef()
        for ringIdx in range(poly.GetGeometryCount()):
            ring = poly.GetGeometryRef(ringIdx)
            for pointId in range(0, ring.GetPointCount()):
                p = ring.GetPoint(pointId)
                # transform to image geo coords
                pImage = [0.0, 0.0]
                pImage[0], pImage[1] = pyproj.transform(vectorProj, imageProj, p[0], p[1])
                # transform to pixels
                pPixels = [int((pImage[0] - minX) / pixelSizeX + 0.5),
                           int((pImage[1] - minY) / pixelSizeY + 0.5)]
                pPixels[0] = pPixels[0] - 1 if pPixels[0] >= inputImage.RasterXSize else pPixels[0]
                pPixels[1] = pPixels[0] - 1 if pPixels[1] >= inputImage.RasterYSize else pPixels[1]
                points.append(pPixels)
            if len(points) > 0:
                polygons[polygonId] = points
                polygonId += 1
    gen_kw18.gen_kw18(polygons, None, args.output_base)
    if args.debug:
        import vtk        
        numberOfPixels = inputImage.RasterXSize * inputImage.RasterYSize
        scalars = vtk.vtkUnsignedCharArray()
        scalars.SetNumberOfComponents(4)
        scalars.SetNumberOfTuples(numberOfPixels)
        # white transparent pixels
        for i in range(3):
            scalars.FillComponent(i, 255)
        scalars.FillComponent(3, 0)
        image = vtk.vtkImageData()
        image.SetDimensions(inputImage.RasterXSize, inputImage.RasterYSize, 1)
        image.SetSpacing(1, 1, 1)
        image.SetOrigin(0, 0, 0)
        image.GetPointData().SetScalars(scalars)
        for i, polygon in polygons.items():
            for point in polygon:
                for x in range(-3, 4, 1):
                    for y in range(-3, 4, 1):
                        p = [point[0] + x, point[1] + y]
                        if (p[0] >= 0 and p[0] < inputImage.RasterXSize and
                            p[1] >= 0 and p[1] < inputImage.RasterYSize):
                            # black opaque 7x7 blocks
                            image.SetScalarComponentFromFloat(p[0], p[1], 0, 0, 0)
                            image.SetScalarComponentFromFloat(p[0], p[1], 0, 1, 0)
                            image.SetScalarComponentFromFloat(p[0], p[1], 0, 2, 0)
                            image.SetScalarComponentFromFloat(p[0], p[1], 0, 3, 255)
        outputNoExt = os.path.splitext(args.output)[0]
        writer = vtk.vtkPNGWriter()
        writer.SetFileName(outputNoExt + '.png')
        writer.SetInputDataObject(image)
        writer.Write()



if __name__ == '__main__':
    import sys
    try:
        main(sys.argv[1:])
    except Exception as e:
        logging.exception(e)
        sys.exit(1)
