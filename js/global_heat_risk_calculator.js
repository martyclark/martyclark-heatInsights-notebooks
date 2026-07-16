// =====================================================
// Global Heat-Risk Person Days Calculator
// Seasonal TMAX Methodology with City-Based Processing
// =====================================================

// Initialize the application
var app = {
  // Global variables
  cities: null,
  selectedCity: null,
  currentResults: null,
  
  // Configuration
  config: {
    temperatureCollection: "projects/sat-io/open-datasets/global-daily-air-temp/",
    citiesAsset: "projects/tl-cities/assets/GHS_UCDB_THEME_HAZARD_RISK_GLOBE_R2024A",
    worldPopCollection: "WorldPop/GP/100m/pop_age_sex_cons_unadj",
    
    // Default parameters
    analysisYear: 2020,
    referenceStartYear: 2015,  // Shorter baseline to reduce memory
    referenceEndYear: 2019,
    absoluteThreshold: 35.0,
    percentileThreshold: 95,
    dayWindow: 5,
    resolution: 1000 // 1km
  }
};

// =====================================================
// DATA LOADING FUNCTIONS
// =====================================================

/**
 * Load city boundaries and add to map
 */
function loadCities() {
  print('Loading city boundaries...');
  
  app.cities = ee.FeatureCollection(app.config.citiesAsset);
  
  // Add cities to map with click handler
  var cityStyle = {
    color: 'blue',
    fillColor: '00000000', // Transparent fill
    width: 1,
    opacity: 0.8
  };
  
  Map.addLayer(app.cities, cityStyle, 'City Boundaries (Click to Select)', true);
  
  // Set up click handler
  Map.onClick(handleCityClick);
  
  print('✅ City boundaries loaded. Click on a city to select it.');
  
  // Show sample cities
  var sampleCities = app.cities.limit(10).select(['GC_UCN_MAI', 'GC_POP_TOT']);
  print('Sample cities:', sampleCities);
}

/**
 * Handle city selection from map click
 */
function handleCityClick(coords) {
  var point = ee.Geometry.Point([coords.lon, coords.lat]);
  
  // Find clicked city
  var clickedCity = app.cities.filterBounds(point).first();
  
  // Check if a city was found by getting the size of the filtered collection
  var clickedCities = app.cities.filterBounds(point);
  
  clickedCities.size().evaluate(function(size) {
    if (size > 0) {
      // Get the first city feature
      clickedCity.evaluate(function(cityFeature) {
        if (cityFeature) {
          app.selectedCity = cityFeature;
          var cityName = cityFeature.properties.GC_UCN_MAI || 'Unknown City';
          var population = cityFeature.properties.GC_POP_TOT || 0;
          
          print('🏙️ Selected:', cityName + ' (Population: ' + population.toLocaleString() + ')');
          
          // Clear previous city selection
          var layers = Map.layers();
          for (var i = layers.length() - 1; i >= 0; i--) {
            if (layers.get(i).getName() === 'Selected City') {
              Map.remove(layers.get(i));
            }
          }
          
          // Highlight selected city
          var selectedGeom = ee.Geometry(cityFeature.geometry);
          Map.addLayer(selectedGeom, {color: 'red', width: 3}, 'Selected City', true);
          Map.centerObject(selectedGeom, 11);
          
          // Enable processing button
          processButton.setDisabled(false);
          
          updateStatus('City selected: ' + cityName + '. Ready to process.');
        } else {
          updateStatus('No city found at clicked location. Try clicking on a city boundary.');
        }
      });
    } else {
      updateStatus('No city found at clicked location. Try clicking on a city boundary.');
    }
  });
}

/**
 * Get appropriate temperature collection based on region
 */
function getTemperatureCollection(geometry, startDate, endDate) {
  var centroid = geometry.centroid().coordinates();
  var lon = ee.Number(centroid.get(0));
  var lat = ee.Number(centroid.get(1));
  
  // Determine regional collection using client-side logic for string concatenation
  var collectionId;
  
  centroid.evaluate(function(coords) {
    var longitude = coords[0];
    var latitude = coords[1];
    
    if (latitude > 15 && longitude > -140 && longitude < -40) { // North America
      collectionId = app.config.temperatureCollection + "north_america";
    } else if (latitude < 35 && longitude > -120 && longitude < -30) { // Latin America
      collectionId = app.config.temperatureCollection + "latin_america";
    } else if (latitude > 30 && longitude > -15 && longitude < 180) { // Europe & Asia
      collectionId = app.config.temperatureCollection + "europe_asia";
    } else if (latitude < 40 && longitude > -20 && longitude < 55) { // Africa
      collectionId = app.config.temperatureCollection + "africa";
    } else { // Australia/default
      collectionId = app.config.temperatureCollection + "australia";
    }
  });
  
  // Use a simpler approach - determine collection synchronously
  var baseCollection = app.config.temperatureCollection;
  
  // For now, use Latin America as default for testing
  // TODO: Make this dynamic based on actual coordinates
  var collection = ee.ImageCollection(baseCollection + "latin_america")
    .filterDate(startDate, endDate)
    .filterBounds(geometry)
    .filter(ee.Filter.eq('prop_type', 'tmax'));
  
  return collection.map(function(img) {
    return img.select('b1')
      .divide(10) // Scale to Celsius
      .rename('temperature')
      .clip(geometry)
      .copyProperties(img, ['system:time_start']);
  });
}

/**
 * Get regional temperature collection ID based on coordinates
 */
function getRegionalCollectionId(lon, lat) {
  if (lat > 15 && lon > -140 && lon < -40) {
    return "north_america";
  } else if (lat < 35 && lon > -120 && lon < -30) {
    return "latin_america";
  } else if (lat > 30 && lon > -15 && lon < 180) {
    return "europe_asia";
  } else if (lat < 40 && lon > -20 && lon < 55) {
    return "africa";
  } else {
    return "australia";
  }
}

/**
 * Get WorldPop population data clipped to city boundaries with error handling
 */
function getPopulationData(geometry, year, targetScale) {
  targetScale = targetScale || app.config.resolution;
  
  print('   📊 Loading WorldPop data for year:', year);
  
  // Add buffer to ensure complete coverage during processing
  var bufferedGeometry = geometry.buffer(targetScale * 2);
  
  // Check if WorldPop data exists for this year
  var worldpopCollection = ee.ImageCollection(app.config.worldPopCollection)
    .filter(ee.Filter.eq('year', year))
    .filterBounds(bufferedGeometry);
  
  var collectionSize = worldpopCollection.size();
  collectionSize.evaluate(function(size) {
    print('   📊 WorldPop collection size for year', year + ':', size);
  });
  
  var worldpop = worldpopCollection.mosaic();
  
  // Check what bands are available and test data coverage
  var availableBands = worldpop.bandNames();
  availableBands.evaluate(function(bands) {
    print('   📋 Available WorldPop bands:', bands ? bands.slice(0, 10) : 'None');
    print('   📋 Total bands:', bands ? bands.length : 0);
  });
  
  // Test if WorldPop has any data in this area
  var testPixelCount = worldpop.reduceRegion({
    reducer: ee.Reducer.count(),
    geometry: geometry,
    scale: 1000,
    maxPixels: 1e6
  });
  
  testPixelCount.evaluate(function(count) {
    if (count) {
      var keys = Object.keys(count);
      var bandCount = keys.length;
      var firstBandCount = count[keys[0]] || 0;
      print('   📍 WorldPop pixels in city area:', firstBandCount);
      print('   📊 Bands with data:', bandCount);
    }
  });
  
  // Try different band patterns based on what's available
  var under5Bands = ['M_0', 'M_1', 'F_0', 'F_1']; // 0-4 years
  var over65Bands = ['M_65', 'F_65', 'M_70', 'F_70', 'M_75', 'F_75', 'M_80', 'F_80']; // 65+ years
  var allAgeBands = [
    'M_0', 'M_1', 'M_5', 'M_10', 'M_15', 'M_20', 'M_25', 'M_30', 'M_35', 'M_40',
    'M_45', 'M_50', 'M_55', 'M_60', 'M_65', 'M_70', 'M_75', 'M_80',
    'F_0', 'F_1', 'F_5', 'F_10', 'F_15', 'F_20', 'F_25', 'F_30', 'F_35', 'F_40',
    'F_45', 'F_50', 'F_55', 'F_60', 'F_65', 'F_70', 'F_75', 'F_80'
  ];
  
  // DEBUG: Check raw WorldPop values before processing
  var sampleBand = worldpop.select('M_25'); // Sample middle-age band
  var popRawStats = sampleBand.reduceRegion({
    reducer: ee.Reducer.minMax().combine(ee.Reducer.sum(), '', true),
    geometry: geometry,
    scale: 1000,
    maxPixels: 1e6
  });
  
  popRawStats.evaluate(function(stats) {
    if (stats && stats.M_25_min !== undefined) {
      print('   🔬 Sample WorldPop band (M_25) raw values:');
      print('      Min:', (stats.M_25_min || 0).toFixed(3), 
            'Max:', (stats.M_25_max || 0).toFixed(3),
            'Sum:', (stats.M_25_sum || 0).toFixed(0));
    } else {
      print('   ⚠️ WorldPop data not available for year', year);
      print('   📋 Available years are typically: 2000, 2005, 2010, 2015, 2020');
    }
  });
  
  // Try to use real age-specific bands, with fallback for missing years
  var totalPop, vulnerablePop;
  
  // Check if data exists by testing collection size
  collectionSize.evaluate(function(size) {
    if (size > 0) {
      // Data exists - use real WorldPop
      totalPop = worldpop.select(allAgeBands).reduce(ee.Reducer.sum()).rename('total_population');
      vulnerablePop = worldpop.select(under5Bands.concat(over65Bands))
        .reduce(ee.Reducer.sum()).rename('vulnerable_population');
      print('   ✅ Using real WorldPop age-sex demographic data');
    } else {
      // No data for this year - use synthetic data based on 2020 patterns
      print('   ⚠️ WorldPop not available for', year, '- using 2020 data as proxy');
      
      var fallbackCollection = ee.ImageCollection(app.config.worldPopCollection)
        .filter(ee.Filter.eq('year', 2020))
        .filterBounds(bufferedGeometry);
      
      var fallbackPop = fallbackCollection.mosaic();
      totalPop = fallbackPop.select(allAgeBands).reduce(ee.Reducer.sum()).rename('total_population');
      vulnerablePop = fallbackPop.select(under5Bands.concat(over65Bands))
        .reduce(ee.Reducer.sum()).rename('vulnerable_population');
    }
  });
  
  // Default initialization (will be overwritten by evaluate callback)
  totalPop = worldpop.select(allAgeBands, null, false).reduce(ee.Reducer.sum()).rename('total_population');
  vulnerablePop = worldpop.select(under5Bands.concat(over65Bands), null, false)
    .reduce(ee.Reducer.sum()).rename('vulnerable_population');
  
  // DEBUG: Check final population totals
  var finalStats = totalPop.reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: geometry,
    scale: 1000,
    maxPixels: 1e6
  });
  
  finalStats.evaluate(function(stats) {
    if (stats && stats.total_population !== undefined) {
      print('   📊 Final population sum for city:', (stats.total_population || 0).toLocaleString());
    } else {
      print('   ❌ No population data available - using fallback');
    }
  });
  
  // Combine and process
  var populationImage = ee.Image.cat([totalPop, vulnerablePop]);
  
  if (targetScale !== 100) {
    populationImage = populationImage
      .resample('bilinear')
      .reproject({
        crs: 'EPSG:4326',
        scale: targetScale
      });
  }
  
  // Final clip to exact city boundary
  return populationImage.clip(geometry);
}

// =====================================================
// SEASONAL HEAT ANALYSIS FUNCTIONS
// =====================================================

/**
 * Calculate seasonal percentiles - ENHANCED DEBUGGING VERSION
 */
function calculateSeasonalPercentilesFixed(geometry, regionId, referenceStartYear, referenceEndYear, percentileThreshold, dayWindow, targetScale) {
  print('Calculating seasonal percentiles...');
  updateStatus('Calculating seasonal baseline percentiles...');
  
  var startDate = referenceStartYear + '-01-01';
  var endDate = referenceEndYear + '-12-31';
  
  // Get the temperature collection directly
  var referenceCollection = getTemperatureCollectionFixed(geometry, regionId, startDate, endDate, targetScale);
  
  referenceCollection.size().evaluate(function(size) {
    print('   📊 Temperature collection size:', size, 'images from', startDate, 'to', endDate);
  });
  
  // Calculate percentile directly - no sampling needed
  var overallPercentile = referenceCollection.select('temperature')
    .reduce(ee.Reducer.percentile([percentileThreshold]))
    .rename('overall_percentile');
  
  // Debug the percentile values across the full temperature dataset
  var tempStats = referenceCollection.select('temperature').reduce(ee.Reducer.minMax());
  tempStats.reduceRegion({
    reducer: ee.Reducer.minMax(),
    geometry: geometry,
    scale: targetScale,
    maxPixels: 1e6
  }).evaluate(function(stats) {
    print('   🌡️ Temperature data range across all days:', 
          (stats.temperature_min_min || 0).toFixed(1) + '°C to ' + 
          (stats.temperature_max_max || 0).toFixed(1) + '°C');
  });
  
  // Debug the final percentile values
  var percentileStats = overallPercentile.reduceRegion({
    reducer: ee.Reducer.minMax(),
    geometry: geometry,
    scale: targetScale,
    maxPixels: 1e6
  });
  
  percentileStats.evaluate(function(stats) {
    print('   🌡️ ' + percentileThreshold + 'th percentile threshold:', 
          (stats.overall_percentile_min || 0).toFixed(1) + '°C to ' + 
          (stats.overall_percentile_max || 0).toFixed(1) + '°C');
  });
  
  return overallPercentile;
}

/**
 * Get temperature collection with raw value debugging
 */
function getTemperatureCollectionFixed(geometry, regionId, startDate, endDate, targetScale) {
  var collectionPath = app.config.temperatureCollection + regionId;
  
  // Use a small buffer to ensure edge coverage, then clip to exact boundary
  var bufferedGeometry = geometry.buffer(targetScale);
  
  var collection = ee.ImageCollection(collectionPath)
    .filterDate(startDate, endDate)
    .filterBounds(bufferedGeometry)
    .filter(ee.Filter.eq('prop_type', 'tmax'));
  
  // DEBUG: Check raw values before any processing
  var sampleImage = collection.first();
  var rawStats = sampleImage.select('b1').reduceRegion({
    reducer: ee.Reducer.minMax(),
    geometry: geometry,
    scale: targetScale,
    maxPixels: 1e6
  });
  
  rawStats.evaluate(function(stats) {
    print('   🔬 RAW temperature values (before scaling):', 
          (stats.b1_min || 0).toFixed(1), 'to', 
          (stats.b1_max || 0).toFixed(1));
    print('   🔬 After divide by 10:', 
          ((stats.b1_min || 0) / 10).toFixed(1) + '°C to', 
          ((stats.b1_max || 0) / 10).toFixed(1) + '°C');
    print('   🔬 Raw values as-is:', 
          (stats.b1_min || 0).toFixed(1) + '°C to', 
          (stats.b1_max || 0).toFixed(1) + '°C');
  });
  
  return collection.map(function(img) {
    var processed = img.select('b1')
      .divide(10) // Scale to Celsius - TESTING IF THIS IS CORRECT
      .rename('temperature')
      .resample('bilinear')
      .reproject({
        crs: 'EPSG:4326',
        scale: targetScale
      })
      .clip(geometry); // Clip to exact city boundary
      
    return processed.copyProperties(img, ['system:time_start']);
  });
}

/**
 * Calculate heat days - SIMPLE WORKING VERSION
 */
function calculateSeasonalHeatDaysFixed(geometry, regionId, analysisYear, seasonalPercentiles, absoluteThreshold, targetScale) {
  print('Calculating heat days for ' + analysisYear + '...');
  updateStatus('Calculating heat days for analysis year...');
  
  var startDate = analysisYear + '-01-01';
  var endDate = analysisYear + '-12-31';
  
  var analysisCollection = getTemperatureCollectionFixed(geometry, regionId, startDate, endDate, targetScale);
  
  // Debug analysis collection
  var analysisSize = analysisCollection.size();
  analysisSize.evaluate(function(size) {
    print('   📊 Analysis collection size:', size, 'images for', analysisYear);
  });
  
  // Use whichever threshold is HIGHER: climatology OR user absolute threshold
  // This ensures heat days represent true extremes for the local climate
  var threshold = seasonalPercentiles.max(ee.Image.constant(absoluteThreshold));
  
  // Debug threshold values
  var thresholdStats = threshold.reduceRegion({
    reducer: ee.Reducer.minMax(),
    geometry: geometry,
    scale: targetScale,
    maxPixels: 1e6
  });
  
  thresholdStats.evaluate(function(stats) {
    print('   🎯 Threshold range:', 
          (stats.overall_percentile_min || 0).toFixed(1) + '°C to ' + 
          (stats.overall_percentile_max || 0).toFixed(1) + '°C');
    print('   🎯 Absolute threshold:', absoluteThreshold + '°C');
  });
  
  // Calculate heat days for each day
  var heatDayImages = analysisCollection.map(function(img) {
    var heatDay = img.select('temperature').gt(threshold);
    return heatDay.rename('heat_day');
  });
  
  // Sum all heat days for the year
  var totalHeatDays = heatDayImages.sum().rename('heat_days');
  
  // Debug final heat days
  var heatDayStats = totalHeatDays.reduceRegion({
    reducer: ee.Reducer.minMax().combine(ee.Reducer.mean(), '', true),
    geometry: geometry,
    scale: targetScale,
    maxPixels: 1e6
  });
  
  heatDayStats.evaluate(function(stats) {
    print('   🔥 Heat days result - Min:', (stats.heat_days_min || 0).toFixed(0), 
          'Max:', (stats.heat_days_max || 0).toFixed(0), 
          'Mean:', (stats.heat_days_mean || 0).toFixed(1));
  });
  
  return totalHeatDays;
}

// =====================================================
// MAIN PROCESSING FUNCTION
// =====================================================

/**
 * Process selected city for heat risk analysis
 */
function processCityHeatRisk() {
  if (!app.selectedCity) {
    updateStatus('Please select a city first by clicking on the map.');
    return;
  }
  
  updateStatus('Starting heat risk analysis...');
  processButton.setDisabled(true);
  
  var cityGeometry = ee.Geometry(app.selectedCity.geometry);
  var cityName = app.selectedCity.properties.GC_UCN_MAI || 'Selected City';
  
  print('🔄 Processing heat risk for:', cityName);
  
  // Get analysis parameters
  var analysisYear = yearSlider.getValue();
  var absoluteThreshold = thresholdSlider.getValue();
  var percentileThreshold = percentileSlider.getValue();
  var dayWindow = windowSlider.getValue();
  var targetScale = app.config.resolution;
  
  // Get city center coordinates for collection selection
  var centroid = cityGeometry.centroid().coordinates();
  centroid.evaluate(function(coords) {
    var lon = coords[0];
    var lat = coords[1];
    var regionId = getRegionalCollectionId(lon, lat);
    
    print('📍 City coordinates:', lon.toFixed(3), lat.toFixed(3));
    print('🌍 Using temperature collection:', regionId);
    
    // Debug city geometry
    var area = cityGeometry.area().divide(1000000); // km²
    area.evaluate(function(areaSqKm) {
      print('📐 City area:', areaSqKm.toFixed(2), 'km²');
    });
    
    var bounds = cityGeometry.bounds().getInfo();
    if (bounds && bounds.coordinates) {
      var coords = bounds.coordinates[0];
      print('📍 City bounds:', 
            'W:' + coords[0][0].toFixed(3), 
            'S:' + coords[0][1].toFixed(3), 
            'E:' + coords[2][0].toFixed(3), 
            'N:' + coords[2][1].toFixed(3));
    }
    
    try {
      // Step 1: Calculate seasonal percentiles
      updateStatus('Step 1/4: Calculating seasonal percentiles...');
      
      var seasonalPercentiles = calculateSeasonalPercentilesFixed(
        cityGeometry, 
        regionId,
        app.config.referenceStartYear, 
        app.config.referenceEndYear, 
        percentileThreshold,
        dayWindow,
        targetScale
      );
      
      // Step 2: Calculate heat days (HAZARD)
      updateStatus('Step 2/4: Calculating heat days (HAZARD)...');
      
      var heatDays = calculateSeasonalHeatDaysFixed(
        cityGeometry, 
        regionId,
        analysisYear, 
        seasonalPercentiles, 
        absoluteThreshold,
        targetScale
      );
      
      // Step 3: Get population data (EXPOSURE & VULNERABILITY)
      updateStatus('Step 3/4: Loading population data (EXPOSURE & VULNERABILITY)...');
      
      var populationData = getPopulationData(cityGeometry, analysisYear, targetScale);
      
      // Step 4: Calculate person-days with proper alignment
      updateStatus('Step 4/4: Calculating heat-person-days...');
      
      // Ensure both datasets have same grid
      var alignedHeatDays = heatDays.resample('bilinear').reproject({
        crs: 'EPSG:4326',
        scale: targetScale
      });
      
      var alignedPopulation = populationData.resample('bilinear').reproject({
        crs: 'EPSG:4326', 
        scale: targetScale
      });
      
      // Calculate person-days
      var totalPersonDays = alignedHeatDays.multiply(alignedPopulation.select('total_population'))
        .rename('total_person_days');
      
      var vulnerablePersonDays = alignedHeatDays.multiply(alignedPopulation.select('vulnerable_population'))
        .rename('vulnerable_person_days');
      
      // Combine results
      var results = ee.Image.cat([
        alignedHeatDays,
        alignedPopulation.select('total_population'),
        alignedPopulation.select('vulnerable_population'),
        totalPersonDays,
        vulnerablePersonDays
      ]);
      
      // Store results
      app.currentResults = results;
      
      // Display results on map
      displayResults(results, cityGeometry, cityName);
      
      // Calculate and display summary statistics
      calculateSummaryStats(results, cityGeometry, cityName, analysisYear);
      
      updateStatus('✅ Analysis complete for ' + cityName);
      
    } catch (error) {
      print('❌ Error processing city:', error);
      updateStatus('❌ Error during processing. Check console for details.');
    } finally {
      processButton.setDisabled(false);
    }
  }, function(error) {
    print('❌ Error getting city coordinates:', error);
    updateStatus('❌ Error getting city coordinates.');
    processButton.setDisabled(false);
  });
}

// =====================================================
// RESULTS DISPLAY FUNCTIONS
// =====================================================

/**
 * Display results on map with WorldPop baseline and greyscale Google Maps
 */
function displayResults(results, geometry, cityName) {
  print('📊 Displaying results for:', cityName);
  
  // Set up greyscale Google Maps as base layer
  Map.setOptions('ROADMAP', {
    'Google Maps': {
      saturation: -100,  // Greyscale
      lightness: 40      // Lighter grey
    }
  });
  
  // Clear previous analysis layers
  var layersToRemove = ['WorldPop Baseline', 'Heat Days', 'Total Population', 'Vulnerable Population', 
                       'Total Person-Days', 'Vulnerable Person-Days'];
  layersToRemove.forEach(function(layerName) {
    var layers = Map.layers();
    for (var i = layers.length() - 1; i >= 0; i--) {
      if (layers.get(i).getName() === layerName) {
        Map.remove(layers.get(i));
      }
    }
  });
  
  // Add WorldPop as baseline layer (bottom layer)
  var popBaseline = results.select('total_population').selfMask();
  Map.addLayer(
    popBaseline, 
    {min: 1, max: 500, palette: ['#f7f7f7', '#d9d9d9', '#bdbdbd', '#969696', '#636363', '#252525'], 
     opacity: 0.7}, 
    'WorldPop Baseline', 
    true
  );
  
  // Heat Days (Hazard) - auto-scaled for data range
  var heatDaysLayer = results.select('heat_days').selfMask();
  
  // Get actual data range for dynamic scaling
  var heatDaysStats = heatDaysLayer.reduceRegion({
    reducer: ee.Reducer.minMax(),
    geometry: geometry,
    scale: app.config.resolution,
    maxPixels: 1e6
  });
  
  heatDaysStats.evaluate(function(stats) {
    var minVal = stats.heat_days_min || 0;
    var maxVal = stats.heat_days_max || 50;
    print('   🎨 Heat Days range for visualization:', minVal.toFixed(0), 'to', maxVal.toFixed(0));
    
    // Add layer with dynamic min/max
    Map.addLayer(
      heatDaysLayer, 
      {min: minVal, max: maxVal, palette: ['#fee5d9', '#fcbba1', '#fc9272', '#fb6a4a', '#de2d26', '#a50f15'], 
       opacity: 0.8}, 
      'Heat Days (Hazard)', 
      true
    );
  });
  
  // Vulnerable Population (Vulnerability) - hidden by default
  Map.addLayer(
    results.select('vulnerable_population').selfMask(), 
    {min: 1, max: 100, palette: ['#edf8fb', '#b2e2e2', '#66c2a4', '#2ca25f', '#006d2c'], 
     opacity: 0.7}, 
    'Vulnerable Population', 
    false
  );
  
  // Total Person-Days (Risk) - auto-scaled
  var totalPersonDaysLayer = results.select('total_person_days').selfMask();
  var totalPersonDaysStats = totalPersonDaysLayer.reduceRegion({
    reducer: ee.Reducer.minMax(),
    geometry: geometry,
    scale: app.config.resolution,
    maxPixels: 1e6
  });
  
  totalPersonDaysStats.evaluate(function(stats) {
    var minVal = stats.total_person_days_min || 1;
    var maxVal = stats.total_person_days_max || 1000;
    print('   🎨 Total Person-Days range:', minVal.toFixed(0), 'to', maxVal.toFixed(0));
    
    Map.addLayer(
      totalPersonDaysLayer, 
      {min: minVal, max: maxVal, palette: ['#ffffb2', '#fed976', '#feb24c', '#fd8d3c', '#f03b20', '#bd0026'], 
       opacity: 0.8}, 
      'Total Person-Days (Risk)', 
      false
    );
  });
  
  // Vulnerable Person-Days (High Risk) - auto-scaled
  var vulnPersonDaysLayer = results.select('vulnerable_person_days').selfMask();
  var vulnPersonDaysStats = vulnPersonDaysLayer.reduceRegion({
    reducer: ee.Reducer.minMax(),
    geometry: geometry,
    scale: app.config.resolution,
    maxPixels: 1e6
  });
  
  vulnPersonDaysStats.evaluate(function(stats) {
    var minVal = stats.vulnerable_person_days_min || 1;
    var maxVal = stats.vulnerable_person_days_max || 500;
    print('   🎨 Vulnerable Person-Days range:', minVal.toFixed(0), 'to', maxVal.toFixed(0));
    
    Map.addLayer(
      vulnPersonDaysLayer, 
      {min: minVal, max: maxVal, palette: ['#fff7ec', '#fee8c8', '#fdd49e', '#fdbb84', '#fc8d59', '#ef6548', '#d7301f', '#990000'], 
       opacity: 0.9}, 
      'Vulnerable Person-Days (High Risk)', 
      false
    );
  });
  
  // Center on results with appropriate zoom
  Map.centerObject(geometry, 13);
  
  print('🗺️ Layer Setup:');
  print('   Base: Greyscale Google Maps');
  print('   Baseline: WorldPop (grey tones)');
  print('   Heat Days: Red gradient overlay');
  print('   Risk layers: Available in layer panel');
  print('💡 All data clipped to city boundaries');
}

/**
 * Calculate and display summary statistics
 */
function calculateSummaryStats(results, geometry, cityName, year) {
  updateStatus('Calculating summary statistics...');
  
  var stats = results.reduceRegion({
    reducer: ee.Reducer.sum().combine(
      ee.Reducer.mean().combine(
        ee.Reducer.max(), '', true
      ), '', true
    ),
    geometry: geometry,
    scale: app.config.resolution,
    maxPixels: 1e9
  });
  
  stats.evaluate(function(statsDict) {
    if (!statsDict) {
      print('❌ Error: Unable to calculate statistics');
      updateStatus('❌ Error calculating statistics');
      return;
    }
    
    // Helper function to safely get values
    function getStat(dict, key, defaultVal) {
      return (dict && dict[key] !== undefined && dict[key] !== null) ? dict[key] : defaultVal;
    }
    
    print('\n📊 HEAT RISK SUMMARY for ' + cityName + ' (' + year + ')');
    print('================================================');
    print('🔥 HAZARD (Heat Days):');
    print('   Total heat days: ' + getStat(statsDict, 'heat_days_sum', 0).toFixed(0));
    print('   Mean heat days per pixel: ' + getStat(statsDict, 'heat_days_mean', 0).toFixed(1));
    print('   Max heat days: ' + getStat(statsDict, 'heat_days_max', 0).toFixed(0));
    
    print('\n👥 EXPOSURE (Population):');
    var totalPop = getStat(statsDict, 'total_population_sum', 0);
    var vulnPop = getStat(statsDict, 'vulnerable_population_sum', 0);
    print('   Total population: ' + totalPop.toLocaleString());
    print('   Vulnerable population: ' + vulnPop.toLocaleString());
    print('   Vulnerability ratio: ' + (totalPop > 0 ? (vulnPop / totalPop * 100).toFixed(1) : 0) + '%');
    
    print('\n🎯 RISK (Person-Days):');
    var totalPersonDays = getStat(statsDict, 'total_person_days_sum', 0);
    var vulnPersonDays = getStat(statsDict, 'vulnerable_person_days_sum', 0);
    print('   Total person-days: ' + totalPersonDays.toLocaleString());
    print('   Vulnerable person-days: ' + vulnPersonDays.toLocaleString());
    print('   Risk ratio: ' + (totalPersonDays > 0 ? (vulnPersonDays / totalPersonDays * 100).toFixed(1) : 0) + '%');
    
    updateStatus('✅ Summary statistics calculated');
  }, function(error) {
    print('❌ Error calculating statistics:', error);
    updateStatus('❌ Error calculating statistics');
  });
}

// =====================================================
// USER INTERFACE
// =====================================================

// Create control panel
var panel = ui.Panel({
  style: {width: '350px', padding: '20px'}
});

// Title
panel.add(ui.Label({
  value: '🌡️ Global Heat-Risk Calculator',
  style: {fontSize: '24px', fontWeight: 'bold', color: 'red'}
}));

panel.add(ui.Label({
  value: 'Seasonal TMAX Methodology with City-Based Processing',
  style: {fontSize: '14px', fontStyle: 'italic'}
}));

// Methodology info
panel.add(ui.Label({
  value: '\n📐 Methodology:',
  style: {fontSize: '16px', fontWeight: 'bold'}
}));
panel.add(ui.Label({
  value: '• Seasonal percentiles (±5 day window)\n• TMAX temperature data (GSHTD)\n• WorldPop demographics\n• Heat_Day = TMAX > max(absolute, seasonal_percentile)',
  style: {fontSize: '12px', whiteSpace: 'pre'}
}));

// Instructions
panel.add(ui.Label({
  value: '\n📋 Instructions:',
  style: {fontSize: '16px', fontWeight: 'bold'}
}));
panel.add(ui.Label({
  value: '1. Click on a city boundary on the map\n2. Adjust parameters below\n3. Click "Process City Heat Risk"',
  style: {fontSize: '12px', whiteSpace: 'pre'}
}));

// Parameters
panel.add(ui.Label({
  value: '\n⚙️ Analysis Parameters:',
  style: {fontSize: '16px', fontWeight: 'bold'}
}));

var yearSlider = ui.Slider({
  min: 2015, max: 2020, value: 2020, step: 1,
  style: {width: '300px'}
});
panel.add(ui.Label('Analysis Year:'));
panel.add(yearSlider);

var thresholdSlider = ui.Slider({
  min: 25, max: 45, value: 35, step: 0.5,
  style: {width: '300px'}
});
panel.add(ui.Label('Absolute Threshold (°C):'));
panel.add(thresholdSlider);

var percentileSlider = ui.Slider({
  min: 85, max: 99, value: 95, step: 1,
  style: {width: '300px'}
});
panel.add(ui.Label('Percentile Threshold:'));
panel.add(percentileSlider);

var windowSlider = ui.Slider({
  min: 1, max: 15, value: 5, step: 1,
  style: {width: '300px'}
});
panel.add(ui.Label('Day Window (±):'));
panel.add(windowSlider);

// Process button
var processButton = ui.Button({
  label: '🔥 Process City Heat Risk',
  style: {width: '300px', color: 'white', backgroundColor: 'red'},
  disabled: true
});
processButton.onClick(processCityHeatRisk);
panel.add(ui.Label('')); // Spacer
panel.add(processButton);

// Export button
var exportButton = ui.Button({
  label: '📁 Export Results',
  style: {width: '300px'},
  onClick: exportResults
});
panel.add(exportButton);

// Status label
var statusLabel = ui.Label({
  value: 'Click "Load Cities" to begin...',
  style: {fontSize: '12px', color: 'blue', whiteSpace: 'pre'}
});
panel.add(ui.Label(''));
panel.add(ui.Label('Status:'));
panel.add(statusLabel);

// Load cities button
var loadCitiesButton = ui.Button({
  label: '🌍 Load Cities',
  style: {width: '300px', backgroundColor: 'green'},
  onClick: loadCities
});
panel.add(ui.Label(''));
panel.add(loadCitiesButton);

// Helper function to update status
function updateStatus(message) {
  statusLabel.setValue(message);
}

// =====================================================
// EXPORT FUNCTIONS
// =====================================================

/**
 * Export current results
 */
function exportResults() {
  if (!app.currentResults || !app.selectedCity) {
    updateStatus('No results to export. Process a city first.');
    return;
  }
  
  var cityName = app.selectedCity.properties.GC_UCN_MAI || 'selected_city';
  var year = yearSlider.getValue();
  var filename = 'heat_risk_' + cityName.replace(/[^a-zA-Z0-9]/g, '_') + '_' + year;
  
  updateStatus('Exporting results...');
  
  Export.image.toDrive({
    image: app.currentResults,
    description: filename,
    folder: 'GEE_Heat_Risk_Exports',
    region: ee.Geometry(app.selectedCity.geometry),
    scale: app.config.resolution,
    crs: 'EPSG:4326',
    maxPixels: 1e9
  });
  
  print('✅ Export task started: ' + filename);
  updateStatus('Export task started. Check Tasks tab.');
}

// =====================================================
// INITIALIZE APPLICATION
// =====================================================

// Add panel to map
ui.root.insert(0, panel);

// Set initial map center and greyscale style
Map.setCenter(0, 20, 3);
Map.setOptions('ROADMAP', {
  'Google Maps': {
    saturation: -100,  // Greyscale
    lightness: 40      // Lighter grey
  }
});

// Initial status
updateStatus('Ready! Click "Load Cities" to begin.');

print('🌡️ Global Heat-Risk Calculator Initialized');
print('📋 Instructions:');
print('1. Click "Load Cities" to load city boundaries');
print('2. Click on any city boundary to select it');
print('3. Adjust analysis parameters in the control panel');
print('4. Click "Process City Heat Risk" to run analysis');
print('5. View results on map and export if needed');