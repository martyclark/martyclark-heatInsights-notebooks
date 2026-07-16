# Simple temperature analysis function - copy this into your notebook

# Import required libraries for temperature trend analysis
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
import calendar
import numpy as np

def create_temperature_trend_analysis():
    """
    Create simple temperature line graph showing daily average maximum temperature
    across all pixels in the ROI for the selected year
    """
    global analysis_geom
    
    if analysis_geom is None:
        print("❌ Please set an ROI first!")
        return
    
    print("📊 Creating simple temperature analysis for your ROI...")
    
    year = year_selector.value
    temp_abs = temp_abs_slider.value
    percentile = percentile_slider.value
    
    try:
        # Get temperature collection for the selected year
        print(f"   📈 Processing daily temperatures for {year}...")
        year_collection = get_temperature_collection(
            analysis_geom, f'{year}-01-01', f'{year}-12-31', 'tmax'
        )
        
        year_count = year_collection.size().getInfo()
        print(f"   Found {year_count} days of data for {year}")
        
        # Get baseline percentile for comparison
        baseline_start, baseline_end = parse_baseline_period(baseline_period.value)
        baseline_collection = get_temperature_collection(
            analysis_geom, baseline_start, baseline_end, 'tmax'
        )
        
        baseline_percentile = baseline_collection.select('temperature').reduce(
            ee.Reducer.percentile([percentile])
        ).clip(analysis_geom)
        
        p_stats = baseline_percentile.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=analysis_geom,
            scale=2000,
            maxPixels=1e6,
            bestEffort=True
        ).getInfo()
        
        baseline_p_value = p_stats.get(f'temperature_p{percentile}', 35.0)
        print(f"   Baseline {percentile}th percentile: {baseline_p_value:.1f}°C")
        
        # Process each day in the year (no sampling)
        daily_temps = []
        day_numbers = []
        
        start_date = datetime(year, 1, 1)
        
        for day_offset in range(365):
            current_date = start_date + timedelta(days=day_offset)
            if current_date.year != year:
                break
                
            date_str = current_date.strftime('%Y-%m-%d')
            next_date_str = (current_date + timedelta(days=1)).strftime('%Y-%m-%d')
            
            try:
                # Get single day collection
                daily_collection = year_collection.filterDate(date_str, next_date_str)
                
                if daily_collection.size().getInfo() > 0:
                    daily_image = daily_collection.first()
                    
                    # Calculate average temperature across ROI
                    stats = daily_image.select('temperature').reduceRegion(
                        reducer=ee.Reducer.mean(),
                        geometry=analysis_geom,
                        scale=1000,
                        maxPixels=1e6,
                        bestEffort=True
                    ).getInfo()
                    
                    avg_temp = stats.get('temperature_mean', None)
                    if avg_temp is not None:
                        daily_temps.append(avg_temp)
                        day_numbers.append(day_offset + 1)
                
                # Progress update every 30 days
                if (day_offset + 1) % 30 == 0:
                    print(f"   Processed {day_offset + 1}/365 days...")
                    
            except Exception as e:
                print(f"   Skipping day {day_offset + 1}: {e}")
                continue
        
        print(f"   ✅ Successfully processed {len(daily_temps)} days")
        
        # Create the plot
        plt.figure(figsize=(15, 8))
        
        # Plot daily average temperatures
        plt.plot(day_numbers, daily_temps, 'b-', linewidth=1.5, label='Daily Average Temperature', alpha=0.8)
        
        # Add horizontal reference lines
        plt.axhline(y=baseline_p_value, color='red', linestyle='--', linewidth=2, 
                   label=f'Baseline {percentile}th Percentile ({baseline_p_value:.1f}°C)')
        plt.axhline(y=temp_abs, color='orange', linestyle='-', linewidth=2, 
                   label=f'User Threshold ({temp_abs}°C)')
        
        # Formatting
        plt.title(f'Daily Average Maximum Temperature - {year}\nROI: {analysis_geom.area().divide(1000000).getInfo():.1f} km²', 
                 fontsize=14, fontweight='bold')
        plt.xlabel('Day of Year')
        plt.ylabel('Temperature (°C)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Add month labels on x-axis
        month_starts = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        plt.xticks(month_starts, month_names)
        
        plt.tight_layout()
        plt.show()
        
        # Print summary statistics
        if daily_temps:
            print(f"\n📊 Temperature Summary for {year}:")
            print(f"   Average temperature: {np.mean(daily_temps):.1f}°C")
            print(f"   Minimum temperature: {np.min(daily_temps):.1f}°C") 
            print(f"   Maximum temperature: {np.max(daily_temps):.1f}°C")
            print(f"   Days above {percentile}th percentile ({baseline_p_value:.1f}°C): {sum(1 for t in daily_temps if t > baseline_p_value)}")
            print(f"   Days above user threshold ({temp_abs}°C): {sum(1 for t in daily_temps if t > temp_abs)}")
        
    except Exception as e:
        print(f"❌ Error in temperature analysis: {e}")
        import traceback
        print(f"   Details: {traceback.format_exc()}")

print("✅ Simple temperature trend analysis function ready")