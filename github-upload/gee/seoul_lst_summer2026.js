// Google Earth Engine: 2026 여름(6~8월) 서울 지표면온도 (Landsat 8/9 C2 L2)
var seoul = ee.Geometry.Rectangle([126.76, 37.41, 127.19, 37.72]);
function prep(img) {
  var qa = img.select('QA_PIXEL');
  var mask = qa.bitwiseAnd(1<<1).eq(0).and(qa.bitwiseAnd(1<<3).eq(0))
    .and(qa.bitwiseAnd(1<<4).eq(0)).and(qa.bitwiseAnd(1<<5).eq(0));
  return img.select('ST_B10').multiply(0.00341802).add(149).subtract(273.15)
    .rename('LST').updateMask(mask);
}
var col = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
  .merge(ee.ImageCollection('LANDSAT/LC09/C02/T1_L2'))
  .filterBounds(seoul).filterDate('2026-06-01', '2026-09-01')
  .filter(ee.Filter.lt('CLOUD_COVER', 60));
print('장면 수', col.size());
var lst = col.map(prep).median().clip(seoul);
Map.centerObject(seoul, 11);
Map.addLayer(lst, {min: 25, max: 50, palette: ['313695','74add1','fed976','fd8d3c','bd0026']}, 'LST');
Export.image.toDrive({image: lst, description: 'Seoul_LST_Summer2026', folder: 'GEE_exports',
  region: seoul, scale: 30, crs: 'EPSG:5179', maxPixels: 1e9});
