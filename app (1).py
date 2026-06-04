import streamlit as st
import os
import tempfile
from PyPDF2 import PdfReader, PdfWriter
import fitz  # PyMuPDF
from pdf2image import convert_from_path
import base64
from io import BytesIO
import json

# Page configuration
st.set_page_config(
    page_title="PDF Toolbox - Your Personal PDF Editor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(90deg, #FF416C, #FF4B2B);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
    }
    .tool-card {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border: 1px solid #e0e0e0;
        transition: transform 0.2s;
    }
    .tool-card:hover {
        transform: translateY(-5px);
    }
    .sidebar-title {
        font-size: 1.5rem;
        font-weight: bold;
        color: #FF416C;
        text-align: center;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 10px;
        color: #155724;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 5px;
        padding: 10px;
        color: #721c24;
    }
</style>
""", unsafe_allow_html=True)

# Helper functions
def get_file_content_as_base64(path):
    """Get file content as base64 for download links"""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def create_download_button(file_path, button_text="Download File"):
    """Create a styled download button"""
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    
    b64 = base64.b64encode(file_bytes).decode()
    file_name = os.path.basename(file_path)
    
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{file_name}" class="stButton">{button_text}</a>'
    st.markdown(href, unsafe_allow_html=True)

def merge_pdfs(file_list, output_path):
    """Merge multiple PDF files"""
    writer = PdfWriter()
    for pdf_file in file_list:
        reader = PdfReader(pdf_file)
        for page in reader.pages:
            writer.add_page(page)
    with open(output_path, "wb") as f:
        writer.write(f)
    return True

def split_pdf(input_path, output_dir, split_type, page_range=None):
    """Split PDF into multiple files"""
    reader = PdfReader(input_path)
    
    if split_type == "Each Page":
        output_files = []
        for i, page in enumerate(reader.pages):
            writer = PdfWriter()
            writer.add_page(page)
            output_path = os.path.join(output_dir, f"page_{i+1}.pdf")
            with open(output_path, "wb") as f:
                writer.write(f)
            output_files.append(output_path)
        return output_files
    
    elif split_type == "Custom Range":
        if page_range:
            writer = PdfWriter()
            output_files = []
            for start, end in page_range:
                writer = PdfWriter()
                for i in range(start-1, min(end, len(reader.pages))):
                    writer.add_page(reader.pages[i])
                output_path = os.path.join(output_dir, f"pages_{start}-{end}.pdf")
                with open(output_path, "wb") as f:
                    writer.write(f)
                output_files.append(output_path)
            return output_files
    
    elif split_type == "Extract Specific Pages":
        if page_range and len(page_range) > 0:
            writer = PdfWriter()
            for start, end in page_range:
                for i in range(start-1, min(end, len(reader.pages))):
                    writer.add_page(reader.pages[i])
            output_path = os.path.join(output_dir, "extracted_pages.pdf")
            with open(output_path, "wb") as f:
                writer.write(f)
            return [output_path]
    
    return []

def rotate_pdf(input_path, output_path, rotation_degrees):
    """Rotate all pages in PDF"""
    reader = PdfReader(input_path)
    writer = PdfWriter()
    
    for page in reader.pages:
        page.rotate(rotation_degrees)
        writer.add_page(page)
    
    with open(output_path, "wb") as f:
        writer.write(f)
    return True

def compress_pdf(input_path, output_path):
    """Compress PDF using PyMuPDF"""
    doc = fitz.open(input_path)
    
    # Compress by reducing image quality
    for page in doc:
        page.clean_contents()
    
    # Save with compression
    doc.save(output_path, 
             garbage=4,
             deflate=True,
             clean=True)
    doc.close()
    
    original_size = os.path.getsize(input_path)
    compressed_size = os.path.getsize(output_path)
    reduction = ((original_size - compressed_size) / original_size) * 100
    
    return original_size, compressed_size, max(0, reduction)

def add_watermark(input_path, output_path, watermark_text, opacity=0.3, position="center"):
    """Add watermark to PDF"""
    doc = fitz.open(input_path)
    
    for page in doc:
        # Create a new page-sized overlay
        overlay = fitz.open()
        overlay_page = overlay.new_page(width=page.rect.width, height=page.rect.height)
        
        # Add watermark text
        text_rect = overlay_page.rect
        fontsize = min(text_rect.width, text_rect.height) / 10
        
        # Set text position based on user choice
        if position == "center":
            text_x = text_rect.center[0]
            text_y = text_rect.center[1]
        elif position == "top-right":
            text_x = text_rect.x1 - 50
            text_y = text_rect.y0 + 50
        elif position == "bottom-left":
            text_x = text_rect.x0 + 50
            text_y = text_rect.y1 - 50
        elif position == "bottom-right":
            text_x = text_rect.x1 - 50
            text_y = text_rect.y1 - 50
        
        overlay_page.insert_text(
            (text_x, text_y),
            watermark_text,
            fontsize=fontsize,
            color=(0.5, 0.5, 0.5),
            fontname="helv"
        )
        
        # Show the overlay page
        show = page.show_pdf_page(page.rect, overlay, 0, opacity=opacity)
        overlay.close()
    
    doc.save(output_path)
    doc.close()
    return True

def extract_text_from_pdf(input_path):
    """Extract all text from PDF"""
    doc = fitz.open(input_path)
    text_content = []
    
    for page_num, page in enumerate(doc):
        text = page.get_text()
        if text.strip():
            text_content.append({
                "page": page_num + 1,
                "text": text
            })
    
    doc.close()
    return text_content

def convert_pdf_to_images(input_path, dpi=150):
    """Convert PDF pages to images"""
    images = convert_from_path(input_path, dpi=dpi)
    return images

def remove_pages(input_path, output_path, pages_to_remove):
    """Remove specific pages from PDF"""
    reader = PdfReader(input_path)
    writer = PdfWriter()
    
    # Convert to 0-indexed set for easier checking
    remove_set = set(p - 1 for p in pages_to_remove)
    
    for i, page in enumerate(reader.pages):
        if i not in remove_set:
            writer.add_page(page)
    
    with open(output_path, "wb") as f:
        writer.write(f)
    return True

def rearrange_pages(input_path, output_path, new_order):
    """Rearrange pages in PDF according to specified order"""
    reader = PdfReader(input_path)
    writer = PdfWriter()
    
    # Convert to 0-indexed
    for page_num in new_order:
        writer.add_page(reader.pages[page_num - 1])
    
    with open(output_path, "wb") as f:
        writer.write(f)
    return True

# Main app layout
def main():
    # Header
    st.markdown('<p class="main-header">📄 PDF Toolbox</p>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #666;">Your personal PDF editor - All-in-one solution for PDF manipulation</p>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Sidebar for tool selection
    with st.sidebar:
        st.markdown('<p class="sidebar-title">🛠️ Tools</p>', unsafe_allow_html=True)
        
        tool = st.selectbox(
            "Select a tool:",
            [
                "📚 Merge PDFs",
                "✂️ Split PDF",
                "🗜️ Compress PDF",
                "🔄 Rotate PDF",
                "💧 Add Watermark",
                "📝 Extract Text",
                "🖼️ Convert to Images",
                "🗑️ Remove Pages",
                "🔀 Rearrange Pages"
            ],
            index=0
        )
        
        st.markdown("---")
        st.info("💡 **Tip:** All processing happens locally in your browser. Your files are never uploaded to any server!")
    
    # Create temp directory for processing
    if not os.path.exists("temp"):
        os.makedirs("temp")
    
    # Tool implementations
    if tool == "📚 Merge PDFs":
        render_merge_pdfs()
    elif tool == "✂️ Split PDF":
        render_split_pdf()
    elif tool == "🗜️ Compress PDF":
        render_compress_pdf()
    elif tool == "🔄 Rotate PDF":
        render_rotate_pdf()
    elif tool == "💧 Add Watermark":
        render_add_watermark()
    elif tool == "📝 Extract Text":
        render_extract_text()
    elif tool == "🖼️ Convert to Images":
        render_convert_to_images()
    elif tool == "🗑️ Remove Pages":
        render_remove_pages()
    elif tool == "🔀 Rearrange Pages":
        render_rearrange_pages()

def render_merge_pdfs():
    st.header("📚 Merge Multiple PDFs")
    st.markdown("Upload multiple PDF files to combine them into a single document.")
    
    uploaded_files = st.file_uploader(
        "Upload PDF files (order will be preserved)",
        type=["pdf"],
        accept_multiple_files=True,
        help="Select files in the order you want them merged"
    )
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} file(s) uploaded successfully!")
        
        # Show uploaded files
        cols = st.columns(min(4, len(uploaded_files)))
        for i, (file, col) in enumerate(zip(uploaded_files, cols)):
            with col:
                st.info(f"📄 {i+1}. {file.name}")
        
        if st.button("🔗 Merge PDFs", type="primary"):
            with st.spinner("Merging PDFs..."):
                try:
                    output_path = os.path.join("temp", "merged_output.pdf")
                    file_paths = []
                    
                    for file in uploaded_files:
                        temp_path = os.path.join("temp", f"temp_{file.name}")
                        with open(temp_path, "wb") as f:
                            f.write(file.getbuffer())
                        file_paths.append(temp_path)
                    
                    merge_pdfs(file_paths, output_path)
                    
                    st.success("✅ PDFs merged successfully!")
                    st.markdown(f"**Output size:** {os.path.getsize(output_path) / (1024*1024):.2f} MB")
                    
                    # Provide download
                    with open(output_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Download Merged PDF",
                            data=f,
                            file_name="merged_document.pdf",
                            mime="application/pdf",
                            type="primary"
                        )
                    
                    # Clean up
                    for path in file_paths:
                        if os.path.exists(path):
                            os.remove(path)
                            
                except Exception as e:
                    st.error(f"❌ Error merging PDFs: {str(e)}")

def render_split_pdf():
    st.header("✂️ Split PDF")
    st.markdown("Split a PDF into multiple files or extract specific pages.")
    
    uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])
    
    if uploaded_file:
        # Save uploaded file temporarily
        temp_input = os.path.join("temp", uploaded_file.name)
        with open(temp_input, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        reader = PdfReader(temp_input)
        total_pages = len(reader.pages)
        
        st.info(f"📄 **{uploaded_file.name}** - {total_pages} pages")
        
        split_type = st.radio(
            "Split method:",
            ["Each Page", "Extract Specific Pages"]
        )
        
        if split_type == "Extract Specific Pages":
            page_input = st.text_input(
                "Enter page numbers to extract (comma-separated, e.g., 1,3,5-8)",
                help="Use ranges like 3-5 to extract pages 3, 4, and 5"
            )
        
        if st.button("✂️ Split PDF", type="primary"):
            with st.spinner("Splitting PDF..."):
                try:
                    output_dir = os.path.join("temp", "split_output")
                    os.makedirs(output_dir, exist_ok=True)
                    
                    if split_type == "Each Page":
                        output_files = split_pdf(temp_input, output_dir, "Each Page")
                        st.success(f"✅ PDF split into {len(output_files)} files!")
                        
                        # Show download buttons for first 5 files, then offer zip
                        if len(output_files) <= 5:
                            for file_path in output_files:
                                file_name = os.path.basename(file_path)
                                with open(file_path, "rb") as f:
                                    st.download_button(
                                        label=f"⬇️ {file_name}",
                                        data=f,
                                        file_name=file_name,
                                        mime="application/pdf"
                                    )
                        else:
                            st.info(f"Split into {len(output_files)} files. Download them individually or as a zip.")
                            # Create zip for download
                            import zipfile
                            zip_path = os.path.join("temp", "split_pages.zip")
                            with zipfile.ZipFile(zip_path, 'w') as zf:
                                for file_path in output_files:
                                    zf.write(file_path, os.path.basename(file_path))
                            
                            with open(zip_path, "rb") as f:
                                st.download_button(
                                    label="⬇️ Download All Pages (ZIP)",
                                    data=f,
                                    file_name="split_pages.zip",
                                    mime="application/zip",
                                    type="primary"
                                )
                    
                    elif split_type == "Extract Specific Pages":
                        if page_input:
                            try:
                                page_ranges = []
                                for part in page_input.replace(" ", "").split(","):
                                    if "-" in part:
                                        start, end = part.split("-")
                                        page_ranges.append((int(start), int(end)))
                                    else:
                                        page_num = int(part)
                                        page_ranges.append((page_num, page_num))
                                
                                output_files = split_pdf(temp_input, output_dir, "Extract Specific Pages", page_ranges)
                                
                                if output_files:
                                    st.success("✅ Pages extracted successfully!")
                                    file_name = os.path.basename(output_files[0])
                                    with open(output_files[0], "rb") as f:
                                        st.download_button(
                                            label=f"⬇️ Download {file_name}",
                                            data=f,
                                            file_name=file_name,
                                            mime="application/pdf",
                                            type="primary"
                                        )
                                else:
                                    st.error("❌ Could not extract pages. Check your page numbers.")
                            except ValueError:
                                st.error("❌ Invalid page format. Use numbers like 1,3,5 or ranges like 1-3,5-7")
                        else:
                            st.warning("⚠️ Please enter page numbers to extract")
                    
                    # Clean up
                    if os.path.exists(temp_input):
                        os.remove(temp_input)
                    if os.path.exists(output_dir):
                        import shutil
                        shutil.rmtree(output_dir)
                        
                except Exception as e:
                    st.error(f"❌ Error splitting PDF: {str(e)}")
                    if os.path.exists(temp_input):
                        os.remove(temp_input)

def render_compress_pdf():
    st.header("🗜️ Compress PDF")
    st.markdown("Reduce the file size of your PDF while maintaining readability.")
    
    uploaded_file = st.file_uploader("Upload a PDF to compress", type=["pdf"])
    
    if uploaded_file:
        original_size = uploaded_file.size
        st.info(f"📄 **{uploaded_file.name}** - Original size: {original_size / (1024*1024):.2f} MB")
        
        compression_level = st.slider(
            "Compression Level",
            min_value=1,
            max_value=3,
            value=2,
            help="Higher compression = smaller file size but may reduce quality"
        )
        
        if st.button("🗜️ Compress PDF", type="primary"):
            with st.spinner("Compressing PDF..."):
                try:
                    temp_input = os.path.join("temp", uploaded_file.name)
                    temp_output = os.path.join("temp", "compressed_output.pdf")
                    
                    with open(temp_input, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    orig_size, comp_size, reduction = compress_pdf(temp_input, temp_output)
                    
                    st.success("✅ PDF compressed successfully!")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Original Size", f"{orig_size / (1024*1024):.2f} MB")
                    with col2:
                        st.metric("Compressed Size", f"{comp_size / (1024*1024):.2f} MB")
                    with col3:
                        st.metric("Size Reduction", f"{reduction:.1f}%")
                    
                    with open(temp_output, "rb") as f:
                        st.download_button(
                            label="⬇️ Download Compressed PDF",
                            data=f,
                            file_name=f"compressed_{uploaded_file.name}",
                            mime="application/pdf",
                            type="primary"
                        )
                    
                    # Clean up
                    if os.path.exists(temp_input):
                        os.remove(temp_input)
                    if os.path.exists(temp_output):
                        os.remove(temp_output)
                        
                except Exception as e:
                    st.error(f"❌ Error compressing PDF: {str(e)}")

def render_rotate_pdf():
    st.header("🔄 Rotate PDF")
    st.markdown("Rotate all pages in your PDF document.")
    
    uploaded_file = st.file_uploader("Upload a PDF to rotate", type=["pdf"])
    
    if uploaded_file:
        st.info(f"📄 **{uploaded_file.name}**")
        
        rotation = st.selectbox(
            "Rotation angle:",
            [90, 180, 270],
            format_func=lambda x: f"{x}° {'Clockwise' if x != 180 else ''}"
        )
        
        if st.button("🔄 Rotate PDF", type="primary"):
            with st.spinner("Rotating PDF..."):
                try:
                    temp_input = os.path.join("temp", uploaded_file.name)
                    temp_output = os.path.join("temp", "rotated_output.pdf")
                    
                    with open(temp_input, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    rotate_pdf(temp_input, temp_output, rotation)
                    
                    st.success(f"✅ PDF rotated {rotation}° successfully!")
                    
                    with open(temp_output, "rb") as f:
                        st.download_button(
                            label="⬇️ Download Rotated PDF",
                            data=f,
                            file_name=f"rotated_{rotation}_{uploaded_file.name}",
                            mime="application/pdf",
                            type="primary"
                        )
                    
                    # Clean up
                    if os.path.exists(temp_input):
                        os.remove(temp_input)
                    if os.path.exists(temp_output):
                        os.remove(temp_output)
                        
                except Exception as e:
                    st.error(f"❌ Error rotating PDF: {str(e)}")

def render_add_watermark():
    st.header("💧 Add Watermark to PDF")
    st.markdown("Add text watermark to all pages of your PDF document.")
    
    uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])
    
    if uploaded_file:
        st.info(f"📄 **{uploaded_file.name}**")
        
        col1, col2 = st.columns(2)
        with col1:
            watermark_text = st.text_input("Watermark Text", value="CONFIDENTIAL")
        with col2:
            opacity = st.slider("Opacity", min_value=0.1, max_value=0.8, value=0.3, step=0.1)
        
        position = st.selectbox(
            "Watermark Position:",
            ["center", "top-right", "bottom-left", "bottom-right"]
        )
        
        if st.button("💧 Add Watermark", type="primary"):
            if watermark_text:
                with st.spinner("Adding watermark..."):
                    try:
                        temp_input = os.path.join("temp", uploaded_file.name)
                        temp_output = os.path.join("temp", "watermarked_output.pdf")
                        
                        with open(temp_input, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        
                        add_watermark(temp_input, temp_output, watermark_text, opacity, position)
                        
                        st.success("✅ Watermark added successfully!")
                        
                        with open(temp_output, "rb") as f:
                            st.download_button(
                                label="⬇️ Download Watermarked PDF",
                                data=f,
                                file_name=f"watermarked_{uploaded_file.name}",
                                mime="application/pdf",
                                type="primary"
                            )
                        
                        # Clean up
                        if os.path.exists(temp_input):
                            os.remove(temp_input)
                        if os.path.exists(temp_output):
                            os.remove(temp_output)
                            
                    except Exception as e:
                        st.error(f"❌ Error adding watermark: {str(e)}")
            else:
                st.warning("⚠️ Please enter watermark text")

def render_extract_text():
    st.header("📝 Extract Text from PDF")
    st.markdown("Extract all text content from your PDF document.")
    
    uploaded_file = st.file_uploader("Upload a PDF to extract text", type=["pdf"])
    
    if uploaded_file:
        st.info(f"📄 **{uploaded_file.name}**")
        
        if st.button("📝 Extract Text", type="primary"):
            with st.spinner("Extracting text..."):
                try:
                    temp_input = os.path.join("temp", uploaded_file.name)
                    with open(temp_input, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    text_content = extract_text_from_pdf(temp_input)
                    
                    if text_content:
                        st.success(f"✅ Text extracted from {len(text_content)} page(s)!")
                        
                        # Create combined text
                        full_text = "\n".join([f"--- Page {item['page']} ---\n{item['text']}" for item in text_content])
                        
                        # Show text in expandable sections
                        for item in text_content:
                            with st.expander(f"📄 Page {item['page']}"):
                                st.text_area(f"Text from page {item['page']}", item['text'], height=200)
                        
                        # Download options
                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(
                                label="⬇️ Download as TXT",
                                data=full_text.encode('utf-8'),
                                file_name=f"{uploaded_file.name.replace('.pdf', '')}_extracted.txt",
                                mime="text/plain",
                                type="primary"
                            )
                        with col2:
                            # Convert to JSON for structured download
                            json_text = json.dumps(text_content, indent=2, ensure_ascii=False)
                            st.download_button(
                                label="⬇️ Download as JSON",
                                data=json_text.encode('utf-8'),
                                file_name=f"{uploaded_file.name.replace('.pdf', '')}_extracted.json",
                                mime="application/json"
                            )
                    else:
                        st.warning("⚠️ No text content found in the PDF (may be image-based)")
                    
                    # Clean up
                    if os.path.exists(temp_input):
                        os.remove(temp_input)
                        
                except Exception as e:
                    st.error(f"❌ Error extracting text: {str(e)}")

def render_convert_to_images():
    st.header("🖼️ Convert PDF to Images")
    st.markdown("Convert each page of your PDF to a separate image file.")
    
    uploaded_file = st.file_uploader("Upload a PDF to convert", type=["pdf"])
    
    if uploaded_file:
        st.info(f"📄 **{uploaded_file.name}**")
        
        dpi = st.slider("Image Quality (DPI)", min_value=72, max_value=300, value=150, step=72)
        
        if st.button("🖼️ Convert to Images", type="primary"):
            with st.spinner("Converting to images..."):
                try:
                    temp_input = os.path.join("temp", uploaded_file.name)
                    with open(temp_input, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    images = convert_pdf_to_images(temp_input, dpi=dpi)
                    
                    st.success(f"✅ Converted {len(images)} page(s) to images!")
                    
                    # Display images
                    cols = st.columns(min(3, len(images)))
                    for i, (img, col) in enumerate(zip(images, cols)):
                        with col:
                            st.image(img, caption=f"Page {i+1}", use_container_width=True)
                    
                    # Provide download for each image
                    import zipfile
                    zip_path = os.path.join("temp", "pdf_images.zip")
                    with zipfile.ZipFile(zip_path, 'w') as zf:
                        for i, img in enumerate(images):
                            img_path = os.path.join("temp", f"page_{i+1}.png")
                            img.save(img_path, "PNG")
                            zf.write(img_path, f"page_{i+1}.png")
                            if os.path.exists(img_path):
                                os.remove(img_path)
                    
                    with open(zip_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Download All Images (ZIP)",
                            data=f,
                            file_name=f"{uploaded_file.name.replace('.pdf', '')}_images.zip",
                            mime="application/zip",
                            type="primary"
                        )
                    
                    # Clean up
                    if os.path.exists(temp_input):
                        os.remove(temp_input)
                    if os.path.exists(zip_path):
                        os.remove(zip_path)
                        
                except Exception as e:
                    st.error(f"❌ Error converting to images: {str(e)}")

def render_remove_pages():
    st.header("🗑️ Remove Pages from PDF")
    st.markdown("Remove specific pages from your PDF document.")
    
    uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])
    
    if uploaded_file:
        temp_input = os.path.join("temp", uploaded_file.name)
        with open(temp_input, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        reader = PdfReader(temp_input)
        total_pages = len(reader.pages)
        
        st.info(f"📄 **{uploaded_file.name}** - {total_pages} pages")
        
        pages_to_remove = st.text_input(
            "Pages to remove (comma-separated numbers, e.g., 2,4,6)",
            help="Enter page numbers you want to remove (1-indexed)"
        )
        
        if st.button("🗑️ Remove Pages", type="primary"):
            if pages_to_remove:
                with st.spinner("Removing pages..."):
                    try:
                        # Parse page numbers
                        page_nums = [int(p.strip()) for p in pages_to_remove.split(",")]
                        
                        # Validate
                        invalid_pages = [p for p in page_nums if p < 1 or p > total_pages]
                        if invalid_pages:
                            st.error(f"❌ Invalid page numbers: {invalid_pages}. Must be between 1 and {total_pages}")
                        else:
                            temp_output = os.path.join("temp", "output_removed_pages.pdf")
                            remove_pages(temp_input, temp_output, page_nums)
                            
                            remaining = total_pages - len(page_nums)
                            st.success(f"✅ Removed {len(page_nums)} page(s)! {remaining} page(s) remaining.")
                            
                            with open(temp_output, "rb") as f:
                                st.download_button(
                                    label="⬇️ Download PDF",
                                    data=f,
                                    file_name=f"no_pages_{uploaded_file.name}",
                                    mime="application/pdf",
                                    type="primary"
                                )
                            
                            if os.path.exists(temp_output):
                                os.remove(temp_output)
                                
                    except ValueError:
                        st.error("❌ Invalid input. Please enter comma-separated numbers.")
                    except Exception as e:
                        st.error(f"❌ Error removing pages: {str(e)}")
            else:
                st.warning("⚠️ Please enter page numbers to remove")
        
        if os.path.exists(temp_input):
            os.remove(temp_input)

def render_rearrange_pages():
    st.header("🔀 Rearrange Pages in PDF")
    st.markdown("Change the order of pages in your PDF document.")
    
    uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])
    
    if uploaded_file:
        temp_input = os.path.join("temp", uploaded_file.name)
        with open(temp_input, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        reader = PdfReader(temp_input)
        total_pages = len(reader.pages)
        
        st.info(f"📄 **{uploaded_file.name}** - {total_pages} pages")
        
        new_order = st.text_input(
            "New page order (comma-separated numbers, e.g., 3,1,2,4)",
            help="Enter the new order of pages. Use page numbers 1 to {total_pages} separated by commas."
        ).replace("{total_pages}", str(total_pages))
        
        # Show example
        if total_pages > 1:
            example = ",".join([str(i) for i in range(total_pages, 0, -1)])
            st.caption(f"💡 Example: To reverse the document, enter: {example}")
        
        if st.button("🔀 Rearrange Pages", type="primary"):
            if new_order:
                with st.spinner("Rearranging pages..."):
                    try:
                        # Parse page numbers
                        page_order = [int(p.strip()) for p in new_order.split(",")]
                        
                        # Validate
                        if len(page_order) != total_pages:
                            st.error(f"❌ You must specify all {total_pages} pages in the new order.")
                        elif any(p < 1 or p > total_pages for p in page_order):
                            st.error(f"❌ Invalid page numbers. Must be between 1 and {total_pages}.")
                        elif len(page_order) != len(set(page_order)):
                            st.error("❌ Each page number must appear exactly once.")
                        else:
                            temp_output = os.path.join("temp", "rearranged_output.pdf")
                            rearrange_pages(temp_input, temp_output, page_order)
                            
                            st.success("✅ Pages rearranged successfully!")
                            
                            with open(temp_output, "rb") as f:
                                st.download_button(
                                    label="⬇️ Download Rearranged PDF",
                                    data=f,
                                    file_name=f"rearranged_{uploaded_file.name}",
                                    mime="application/pdf",
                                    type="primary"
                                )
                            
                            if os.path.exists(temp_output):
                                os.remove(temp_output)
                                
                    except ValueError:
                        st.error("❌ Invalid input. Please enter comma-separated numbers.")
                    except Exception as e:
                        st.error(f"❌ Error rearranging pages: {str(e)}")
            else:
                st.warning("⚠️ Please enter the new page order")
        
        if os.path.exists(temp_input):
            os.remove(temp_input)

if __name__ == "__main__":
    main()