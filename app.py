import streamlit as st
import PIL.Image
from PIL import ImageCms
import numpy as np
import os
from pathlib import Path

def apply_icc_profile(image_path, icc_path):
    """Apply ICC profile to image"""
    try:
        # Open the image
        img = PIL.Image.open(image_path)
        
        # Create color transform
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        # Load ICC profile
        if icc_path:
            input_profile = ImageCms.getOpenProfile(icc_path)
            output_profile = ImageCms.createProfile('sRGB')
            
            # Create transform with rendering intent parameter (Item 3 eklenmiştir)
            transform = ImageCms.buildTransformFromOpenProfiles(
                input_profile, output_profile, 'RGB', 'RGB',
                renderingIntent=ImageCms.INTENT_PERCEPTUAL
            )
            
            # Apply transform
            img = ImageCms.applyTransform(img, transform)
            
        return img
    except Exception as e:
        st.error(f"Error applying ICC profile: {str(e)}")
        return None

def apply_lighting_condition(img, temperature, brightness):
    """Apply lighting condition to image"""
    try:
        # Convert to numpy array
        img_array = np.array(img).astype(float)
        
        # Temperature adjustment (simple approximation)
        # Warmer temperatures increase red, decrease blue
        # Cooler temperatures increase blue, decrease red
        temperature_factor = (temperature - 5000) / 5000  # Normalize around 5000K
        
        # Adjust RGB channels
        img_array[:,:,0] *= (1 + 0.2 * temperature_factor)  # Red
        img_array[:,:,2] *= (1 - 0.2 * temperature_factor)  # Blue
        
        # Brightness adjustment
        img_array *= brightness
        
        # Clip values to valid range
        img_array = np.clip(img_array, 0, 255)
        
        # Convert back to uint8
        img_array = img_array.astype(np.uint8)
        
        return PIL.Image.fromarray(img_array)
    except Exception as e:
        st.error(f"Error applying lighting condition: {str(e)}")
        return None

def main():
    st.title("Tile Lighting Simulator")
    
    # File uploaders
    image_file = st.file_uploader("Upload Tile Image (TIFF)", type=['tiff', 'tif'])
    icc_file = st.file_uploader("Upload ICC Profile", type=['icc'])
    
    # Lighting controls
    temperature = st.slider("Color Temperature (K)", 2700, 6500, 5000)
    brightness = st.slider("Brightness", 0.5, 1.5, 1.0)
    
    if image_file and icc_file:
        # Save uploaded files temporarily
        temp_image_path = "temp_image.tiff"
        temp_icc_path = "temp_icc.icc"
        
        with open(temp_image_path, "wb") as f:
            f.write(image_file.getbuffer())
        with open(temp_icc_path, "wb") as f:
            f.write(icc_file.getbuffer())
            
        # Process image
        try:
            # Apply ICC profile
            img_with_icc = apply_icc_profile(temp_image_path, temp_icc_path)
            
            if img_with_icc:
                # Apply lighting condition
                final_img = apply_lighting_condition(img_with_icc, temperature, brightness)
                
                if final_img:
                    # Display results
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("Original Image")
                        st.image(img_with_icc)
                    with col2:
                        st.subheader("Adjusted Image")
                        st.image(final_img)
                        
                    # Add download button for processed image
                    if st.button("Download Processed Image"):
                        final_img.save("processed_image.png")
                        with open("processed_image.png", "rb") as file:
                            st.download_button(
                                label="Download Image",
                                data=file,
                                file_name="processed_image.png",
                                mime="image/png"
                            )
        
        except Exception as e:
            st.error(f"Error processing image: {str(e)}")
            
        # Cleanup temporary files
        try:
            os.remove(temp_image_path)
            os.remove(temp_icc_path)
        except:
            pass

if __name__ == "__main__":
    main()
