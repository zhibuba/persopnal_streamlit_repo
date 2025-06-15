import streamlit as st
import os
import json
from nsfw import NsfwNovelWriter
from domains import NSFWNovel

if not os.environ["OPENAI_API_KEY"]:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

st.title("NSFW 小说生成器")
st.markdown("""
请输入你的 NSFW 小说需求，点击生成后将展示小说的标题和概要。
""")

# 注入自适应高度的CSS
st.markdown("""
    <style>
    textarea[data-baseweb="textarea"] {
        min-height: 60px !important;
        max-height: 600px !important;
        height: auto !important;
        overflow-y: auto !important;
        resize: vertical !important;
    }
    </style>
""", unsafe_allow_html=True)

# 初始化/恢复 writer
if 'writer' not in st.session_state:
    st.session_state['writer'] = NsfwNovelWriter()
writer: NsfwNovelWriter = st.session_state['writer']
state = writer.state

# 需求输入
requirements = st.text_area(
    "输入你的 NSFW 小说需求：",
    height=150,
    value=state.requirements or "",
    key="requirements_input"
)
writer.state.requirements = requirements

# 生成按钮
if st.button("生成小说概要"):
    if requirements.strip():
        writer.design_overall(requirements)
        st.success("生成成功！")
    else:
        st.warning("请输入需求后再生成。")

# 重置按钮
if st.button("重置"):
    st.session_state['writer'] = NsfwNovelWriter()
    st.success("已重置所有内容！")
    st.rerun()

# 导出/导入state
col_export, col_import = st.columns(2)
with col_export:
    if st.button("导出为JSON"):
        st.download_button(
            label="下载JSON",
            data=json.dumps(state.model_dump(), ensure_ascii=False, indent=2),
            file_name=f"{state.title or 'NSFW小说'}.json",
            mime="application/json"
        )
with col_import:
    uploaded = st.file_uploader("从JSON导入", type=["json"], key="import_json_uploader")
    if uploaded is not None:
        try:
            data = json.load(uploaded)
            st.session_state['import_json_data'] = data
            st.success("文件已选择，请点击下方按钮应用。")
        except Exception as e:
            st.error(f"文件解析失败: {e}")
    if 'import_json_data' in st.session_state:
        if st.button("应用导入内容"):
            try:
                st.session_state['writer'] = NsfwNovelWriter()
                st.session_state['writer'].state = NSFWNovel.model_validate(st.session_state['import_json_data'])
                st.success("导入成功！")
                st.session_state.pop("import_json_uploader", None)
                st.session_state.pop("import_json_data", None)
                st.rerun()
            except Exception as e:
                st.error(f"导入失败: {e}")

# 标题和概要编辑
if state.title is not None:
    # 导出markdown按钮（移动到概要之上，并同列）
    col_md1, col_md2 = st.columns(2)
    with col_md1:
        if st.button('生成导出文件'):
            writer.export_markdown()
            st.success('已生成导出文件！')
    with col_md2:
        if state.exported_markdown:
            st.download_button('下载导出Markdown', data=state.exported_markdown, file_name=f"{state.title or 'NSFW小说'}.md", mime='text/markdown')

    title = st.text_input("小说标题：", value=state.title or "", key="title_input")
    overall = st.text_area("小说概要：", value=state.overview or "", key="overview_input")
    state.title = title
    state.overview = overall
    st.subheader("角色列表：")
    # 角色展示、编辑、删除
    remove_idx = None
    for idx, character in enumerate(state.characters):
        col1, col2, col3 = st.columns([4, 8, 2])
        with col1:
            edited_name = st.text_input(f"角色名{idx+1}", value=character.name, key=f"character_name_{idx}")
        with col2:
            edited_desc = st.text_input(f"角色描述{idx+1}", value=character.description, key=f"character_desc_{idx}")
        with col3:
            if st.button("删除", key=f"remove_character_{idx}"):
                remove_idx = idx
        # 写回编辑
        state.characters[idx].name = edited_name
        state.characters[idx].description = edited_desc
    if remove_idx is not None:
        del state.characters[remove_idx]
        st.rerun()
    # 增加角色（同一行，on_click清空输入）
    def _add_character_inputs():
        from domains import NSFWCharacter
        if new_char_name.strip():
            state.characters.append(NSFWCharacter(name=new_char_name, description=new_char_desc))
            st.session_state["add_character_name"] = ""
            st.session_state["add_character_desc"] = ""
    coln1, coln2, coln3 = st.columns([4, 8, 2])
    with coln1:
        new_char_name = st.text_input("新增角色名", value="", key="add_character_name")
    with coln2:
        new_char_desc = st.text_input("新增角色描述", value="", key="add_character_desc")
    with coln3:
        add_char_clicked = st.button("添加角色", key="add_character_btn", on_click=_add_character_inputs)
    
       # st.rerun()

    # 角色列表直接由state.characters渲染，无需单独生成按钮
    # rerender函数已移除，直接用st.rerun()

    # 章生成按钮逻辑不变

    col_ch1, col_ch2 = st.columns([2,2])
    with col_ch1:
        chapter_count = st.selectbox("章数量", options=["AUTO"] + [str(i) for i in range(1, 21)], index=0, key="chapter_count")
    with col_ch2:
        if st.button('生成章概要'):
            if state.title and state.overview and state.language and state.characters:
                writer.design_chapters(chapter_count=None if chapter_count=="AUTO" else int(chapter_count))
                for chapter in state.chapters:
                    chapter.sections.clear()
                st.success('章概要生成成功！')
                st.rerun()
            else:
                st.warning('请先生成小说概要后再生成章概要。')

    # 展示章概要及其节编辑与生成
    if state.chapters:
        tab_titles = [chapter.title or f"第{idx+1}章" for idx, chapter in enumerate(state.chapters)]
        tabs = st.tabs(tab_titles)
        for idx, (chapter, tab) in enumerate(zip(state.chapters, tabs)):
            with tab:
                # 章操作按钮同行：左侧新增章，右侧删除本章
                col_ch_add, col_ch_del = st.columns([2,2])
                with col_ch_add:
                    if st.button(f"添加下一章", key=f"add_chapter_after_{idx}"):
                        from domains import NSFWChapter
                        state.chapters.insert(idx+1, NSFWChapter(title="", overview="", sections=[]))
                        st.rerun()
                with col_ch_del:
                    if st.button(f"删除本章", key=f"delete_chapter_{idx}"):
                        del state.chapters[idx]
                        st.rerun()
                # 章标题和概要可编辑
                chapter_title = st.text_input(f"第{idx+1}章标题", value=chapter.title or f"第{idx+1}章", key=f"chapter_title_{idx}")
                chapter_overview = st.text_area(f"第{idx+1}章概要", value=chapter.overview or "", key=f"chapter_overview_{idx}")
                chapter.title = chapter_title
                chapter.overview = chapter_overview
                # 节数量选择+生成节按钮同列
                col_sec1, col_sec2 = st.columns([2,2])
                with col_sec1:
                    section_count = st.selectbox(f"节数量", options=["AUTO"] + [str(i) for i in range(1, 21)], index=0, key=f"section_count_{idx}")
                with col_sec2:
                    if st.button(f"为本章生成节", key=f"gen_sections_{idx}"):
                        writer.design_sections(idx, section_count=None if section_count=="AUTO" else int(section_count))
                        st.success(f"已为{chapter_title}生成节！")
                        st.rerun()
                # 展示并可编辑sections
                for sidx, section in enumerate(chapter.sections):
                    col_secA, col_secB = st.columns([4, 8])
                    with col_secA:
                        sec_title = st.text_input(f"第{idx+1}章第{sidx+1}节标题", value=section.title or "", key=f"section_title_{idx}_{sidx}")
                    with col_secB:
                        sec_overview = st.text_area(f"第{idx+1}章第{sidx+1}节概要", value=section.overview or "", key=f"section_overview_{idx}_{sidx}")
                    # 生成正文按钮
                    if st.button(f"生成第{idx+1}章第{sidx+1}节正文", key=f"gen_content_{idx}_{sidx}"):
                        writer.write_section_content(idx, sidx)
                        st.success(f"已为第{idx+1}章第{sidx+1}节生成正文！")
                        st.rerun()
                    # 写回state
                    section.title = sec_title
                    section.overview = sec_overview
                    # 正文内容自适应高度（仅当section.content不为None时显示）
                    if section.content is not None:
                        sec_content = st.text_area(
                            f"第{idx+1}章第{sidx+1}节内容",
                            value=section.content,
                            key=f"section_content_{idx}_{sidx}",
                            height=400  # 设置较大的默认高度
                        )
                        section.content = sec_content
                                        # 节操作按钮同行：左侧新增节，右侧删除本节
                    col_sec_add, col_sec_del = st.columns([2,2])
                    with col_sec_add:
                        if st.button(f"添加下一节", key=f"add_section_after_{idx}_{sidx}"):
                            from domains import NSFWSection
                            chapter.sections.insert(sidx+1, NSFWSection(title="", overview="", content=None))
                            st.rerun()
                    with col_sec_del:
                        if st.button(f"删除本节", key=f"delete_section_{idx}_{sidx}"):
                            del chapter.sections[sidx]
                            st.rerun()
                    # 角色当前状态展示（衣着、心理、生理），默认折叠，可展开并编辑
                    if section.after_state:
                        with st.expander("本节后角色状态（点击展开/收起）", expanded=False):
                            for cname, cstate in section.after_state.items():
                                st.markdown(f"**{cname}**")
                                clothing = st.text_input(f"{cname} 衣着状态", value=getattr(cstate, 'clothing', ''), key=f"afterstate_clothing_{idx}_{sidx}_{cname}")
                                psychological = st.text_area(f"{cname} 心理状态", value=getattr(cstate, 'psychological', ''), key=f"afterstate_psy_{idx}_{sidx}_{cname}")
                                physiological = st.text_area(f"{cname} 生理状态", value=getattr(cstate, 'physiological', ''), key=f"afterstate_phy_{idx}_{sidx}_{cname}")
                                # 写回
                                cstate.clothing = clothing
                                cstate.psychological = psychological
                                cstate.physiological = physiological

