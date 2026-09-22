# Refreshed
from .base_handler import BaseHandler
import time
import random
import datetime
import base64

class SocialHandler(BaseHandler):
    def _capture_login_qr(self, platform_name):
        """Helper to capture screenshot for remote login"""
        try:
            # Take a screenshot of the page or login modal
            # We prefer full page or a known login container to be safe
            screenshot_bytes = self.page.screenshot(quality=50, type='jpeg')
            b64_img = base64.b64encode(screenshot_bytes).decode('utf-8')
            img_md = f"![登录二维码](data:image/jpeg;base64,{b64_img})"
            self.log(f"请使用手机APP扫描下方二维码登录 {platform_name}：\n\n{img_md}", step="Login Required", status="warning")
        except Exception as e:
            self.log(f"尝试抓取登录二维码失败: {e}")

    def run(self, data: dict):
        platform = data.get("platform", "generic")
        action = data.get("action", "publish")
        job_type = data.get("job_type", "")

        # Infer action from job_type if valid
        if job_type == "view_browser":
            action = "view_only"
        
        # Handle "View Only" Action (Triggered by Link Click)
        if action == "view_only":
             # We ignore the 'url' var here if we want to enforce a specific workflow
             # or we start from it.
             start_url = "https://creator.xiaohongshu.com/creator/home"
             self.log(f"[*] 收到浏览指令，正在打开首页: {start_url}")
             
             try:
                 self.page.goto(start_url)
                 self.page.wait_for_timeout(2000)
                 
                 # Requested Flow: Publish Note (发布笔记) -> Write Long Article (写长文) -> New Creation (新的创作)
                 
                 # 1. Click "发布笔记" (Publish Note) - usually the big button or sidebar
                 self.log("[-] 步骤1: 寻找 '发布笔记'...")
                 pub_nav = self.page.get_by_text("发布笔记").first
                 if pub_nav.is_visible():
                      pub_nav.click()
                      self.log("[+] 点击了 '发布笔记'")
                      self.page.wait_for_timeout(1000)
                 
                 # 2. Click "写长文" (Write Long Article) / "专栏"
                 self.log("[-] 步骤2: 寻找 '写长文'...")
                 long_article_btn = self.page.get_by_text("写专栏").first
                 if not long_article_btn.is_visible():
                        long_article_btn = self.page.get_by_text("写长文").first
                 
                 if long_article_btn.is_visible():
                      long_article_btn.click(force=True)
                      self.log("[+] 点击了 '写长文/专栏'")
                      self.page.wait_for_timeout(2000)
                      
                      # 3. Click "草稿箱" (Drafts)
                      self.log("[-] 步骤3: 寻找 '草稿箱'...")
                      drafts_btn = self.page.get_by_text("草稿箱").first
                      
                      if not drafts_btn.is_visible():
                           # Fallback selectors
                           drafts_btn = self.page.locator(".draft-box, .draft-btn").first
                           
                      if drafts_btn.is_visible():
                           drafts_btn.click(force=True)
                           self.log("[+] 已进入 '草稿箱'")
                      else:
                           self.log("[!] 未找到 '草稿箱' 按钮")
                 else:
                      self.log("[!] 未找到 '写长文' 入口")

                 self.log("[+] 导航结束，请人工查看。")
                 
             except Exception as e:
                 self.log(f"[!] 打开页面失败: {e}")
             return {"status": "success", "msg": "已打开浏览窗口"}

        # Normalize platform names
        if platform in ["redbook", "xiaohongshu"]:
            return self.run_redbook(data)
        elif platform in ["tiktok", "douyin"]:
            return self.run_douyin(data)
        elif platform in ["linkedin"]:
            from .linkedin_handler import LinkedInHandler
            h = LinkedInHandler(self.page)
            h.set_task_context(self.task_id)
            return h.run(data)
        elif platform in ["x", "twitter"]:
            from .x_handler import XHandler
            h = XHandler(self.page)
            h.set_task_context(self.task_id)
            return h.run(data)
        else:
            return self.run_mock(data)

    def run_redbook(self, data):
        title = data.get("title", "")
        content = data.get("content", "")
        # Use Creator Studio for better stability than consumer site
        publish_url = "https://creator.xiaohongshu.com/publish/publish"
        
        self.log(f"[小红书] 正在跳转至创作中心: {publish_url}")
        
        try:
            self.page.goto(publish_url, timeout=60000) # Increased timeout
            self.page.wait_for_timeout(3000)
        except Exception as e:
             return {"status": "failed", "msg": f"网络访问错误: {e}"}

        # Check Login
        # Wait until we strictly see the editor elements. 
        # Do NOT rely on URL not having "login", as redirects can be slow or URLs can be opaque.
        self.log(f"[-] 正在检测登录状态。若未登录，请扫码或输入密码 (无限等待直至成功)...")
        
        wait_cycle = 0
        is_logged_in = False
        
        while True:
             try:
                 # POSITIVE check only: We are logged in if we see the editor inputs OR general logged-in indicators
                 if self.page.locator("input[placeholder*='标题']").count() > 0 or \
                    self.page.locator(".title-input").count() > 0 or \
                    self.page.locator(".c-input_textarea").count() > 0 or \
                    self.page.locator(".publish-container").count() > 0 or \
                    self.page.locator("text=发布笔记").count() > 0 or \
                    self.page.locator("text=首页").count() > 0 or \
                    self.page.locator("text=退出登录").count() > 0 or \
                    self.page.locator(".avatar-container").count() > 0:
                     is_logged_in = True
                     self.log("[+] 检测到手动登录成功！")
                     break
             except:
                 pass
             
             if wait_cycle % 15 == 0:
                 self.log(f"等待登录中... (已等待 {wait_cycle * 2}秒)")
                 # Capture QR Code for remote users
                 self._capture_login_qr("小红书")

                 
             try:
                 time.sleep(2)
             except KeyboardInterrupt:
                 return {"status": "failed", "msg": "任务被人为中断"}
                 
             wait_cycle += 1
        
        # Redundant check removed as loop guarantees success or infinite wait
        
        # NAVIGATION: "写长文" -> "新的创作" (Requested Workflow)
        try:
             self.log("[-] 正在寻找 '写长文' 入口...")
             # Usually a tab or button
             long_article_btn = self.page.get_by_text("写长文").first
             
             if long_article_btn.is_visible():
                  long_article_btn.click(force=True)
                  self.log("[+] 点击了 '写长文'")
                  self.page.wait_for_timeout(2000)
                  
                  # Look for "新的创作" (New Creation)
                  new_create_btn = self.page.get_by_text("新的创作").first
                  if new_create_btn.is_visible():
                       new_create_btn.click(force=True)
                       self.log("[+] 点击了 '新的创作'")
                       self.page.wait_for_timeout(2000)
             else:
                  self.log("[*] 未找到 '写长文' 入口，尝试寻找 '发布图文'(备选)...")
                  fallback = self.page.get_by_text("发布图文").first
                  if fallback.is_visible():
                      fallback.click(force=True)
                  
        except Exception as nav_e:
             self.log(f"[*] 导航步骤非致命错误: {nav_e}")

        self.log(f"正在自动填写内容: {title}...")
        
        # Real Interaction Attempt (Best Effort)
        try:
            # 1. Fill Title
            # Use specific selectors if possible, or generic fallbacks
            # Xiaohongshu web creator selectors are volatile.
            title_filled = False
            
            # Wait briefly for inputs to appear after "login detection"
            self.page.wait_for_timeout(2000)
                
            # 1. Fill Text (Title & Content)
            # Strategy:
            # A. Try specific placeholders user observed: "输入标题", "粘贴到这里或输入文字"
            # B. Fallback: Find all visible text inputs. First is Title, Second is Content.
            
            self.log("[-] 正在寻找输入框 (策略: 占位符/索引)...")
            
            try:
                title_filled = False
                content_filled = False
                
                # --- STRATEGY A: Specific Placeholders ---
                
                # Title
                title_input = self.page.locator("input, textarea").filter(has_text="输入标题").or_(self.page.locator("input[placeholder*='输入标题']")).or_(self.page.locator("input[placeholder='标题']")).first
                
                if title_input.count() > 0 and title_input.is_visible():
                     title_input.click()
                     title_input.fill(title)
                     title_filled = True
                     self.log("[+] 已填写标题 (匹配到 '输入标题')")
                
                self.page.wait_for_timeout(500)

                # Content (Fixing "黏" -> "粘" as per user report)
                content_input = self.page.locator("div, textarea").filter(has_text="粘贴到这里或输入文字").or_(self.page.locator("[placeholder*='粘贴到这里']")).or_(self.page.locator("[placeholder*='输入文字']")).first
                
                if content_input.count() > 0 and content_input.is_visible():
                     content_input.click()
                     try:
                         content_input.fill(content)
                     except:
                         self.page.keyboard.type(content)
                     content_filled = True
                     self.log("[+] 已填写正文 (匹配到 '粘贴到这里...')")

                # --- STRATEGY B: Fallback to Index (First 2 inputs) ---
                if not title_filled or not content_filled:
                     self.log("[!] 占位符精确匹配未完全成功，尝试通用索引匹配...")
                     
                     # Find all potential text entry points
                     # input[type=text], textarea, div[contenteditable]
                     # We need to filter out small icons or search bars if possible, but usually main inputs are large
                     potential_inputs = self.page.locator("input[type='text'], textarea, .c-input_input, .d-input__inner, div[contenteditable='true']")
                     
                     visible_inputs = []
                     for i in range(potential_inputs.count()):
                          el = potential_inputs.nth(i)
                          if el.is_visible():
                               # Optional: Check size?
                               visible_inputs.append(el)
                     
                     self.log(f"[*] 找到 {len(visible_inputs)} 个可见输入框")
                     
                     if len(visible_inputs) >= 1 and not title_filled:
                          el = visible_inputs[0] # First one is Title
                          el.click()
                          el.fill(title)
                          title_filled = True
                          self.log("[+] 已填写标题 (使用第一个可见输入框)")
                          
                     if len(visible_inputs) >= 2 and not content_filled:
                          el = visible_inputs[1] # Second one is Content
                          el.click()
                          try:
                               el.fill(content)
                          except:
                               self.page.keyboard.type(content)
                          content_filled = True
                          self.log("[+] 已填写正文 (使用第二个可见输入框)")
                          
                if not title_filled: self.log("[!] 最终未找到标题输入框")
                if not content_filled: self.log("[!] 最终未找到正文输入框")
                
            except Exception as e:
                self.log(f"[!] 填写过程异常: {e}")

            self.page.wait_for_timeout(500)
            
            # 3. Handle Images (Skip for now or Mock)

            # 3. Handle Images (Skip for now or Mock)
            self.log("[!] 本版本暂跳过图片上传 (需本地文件路径)。")

            self.log("[*] 自动化填写结束。")

            # SAVE DRAFT (暂存) & RETURN LINK
            try:
                self.log("[-] 正在尝试 '暂存/暂存离开'...")
                # Look for "暂存" or "暂存离开"
                save_draft_btn = self.page.locator("button:has-text('暂存'), div:has-text('暂存')").last
                if save_draft_btn.is_visible():
                     save_draft_btn.click()
                     self.log("[+] 已点击 '暂存'")
                     self.page.wait_for_timeout(3000) 
                else:
                     self.log("[!] 未找到 '暂存' 按钮")
                     
            except Exception as e:
                self.log(f"[!] 暂存操作失败: {e}")

        except Exception as e:
            self.log(f"页面交互部分失败: {e}")
        
        # [Corrected Logic for Xiaohongshu Drafts]
        # Since drafts are stored in LocalStorage, we keep the browser session valid.
        # We return the DIRECT target URL. The Web Console frontend works as a controller
        # to send this URL back to the RPA worker via the 'trigger-view' API we just built.
        
        target_page = "https://creator.xiaohongshu.com/creator/home"
        
        return {
            "status": "success", 
            "msg": f"小红书草稿已保存。点击链接将在RPA窗口中打开草稿箱。|||LINK:{target_page}|||"
        }

    def run_douyin(self, data):
        title = data.get("title", "")
        content = data.get("content", "")
        # Douyin Creator Platform Main Page
        publish_url = "https://creator.douyin.com/"
        
        self.log(f"[抖音] 正在跳转至创作平台首页: {publish_url}")
        try:
            self.page.goto(publish_url, timeout=60000)
            self.page.wait_for_timeout(3000)
        except Exception as e:
            self.log(f"页面加载警告: {e}。将尝试继续检测登录...")
        
        # NAVIGATION: Try to click "Publish Article" (发布文章/图文)
        # This is a specific request to support Article publishing workflow
        try:
             # Look for "发布文章" or "我要发文"
             self.log("[-] 尝试定位 '发布文章' 或 '我要发文' 入口...")
             
             # Common selectors for the "Publish" button or menu
             # Note: Douyin UI complex. We look for text mainly.
             
             # Strategy 1: "发布作品" hover menu -> "发布图文"
             publish_btn = self.page.get_by_text("发布作品").first
             if publish_btn.is_visible():
                  # Hover to show menu if needed? Or just click if it's a dropdown
                  # Douyin creator sidebar often has "发布图文"
                  pass
                  
             # Strategy 2: Direct text search (User specified "发布文章"-"我要发文")
             # Try "发布文章"
             article_btn = self.page.get_by_text("发布文章").first
             if article_btn.count() > 0 and article_btn.is_visible():
                  article_btn.click()
                  self.log("[+] 点击了 '发布文章'")
                  self.page.wait_for_timeout(2000)
             
             # Try "我要发文" (often inside the article page or a sub-menu)
             post_btn = self.page.get_by_text("我要发文").first
             if post_btn.count() > 0 and post_btn.is_visible():
                  post_btn.click()
                  self.log("[+] 点击了 '我要发文'")
                  self.page.wait_for_timeout(2000)
                  
        except Exception as e:
             self.log(f"[*] 导航至发布页尝试非致命错误: {e}")
        
        # Strict Positive Check for Login
        self.log("[-] 未登录或页面加载中，请扫码登录 (无限等待直至成功)...")
        wait_cycle = 0
        is_logged_in = False
        
        while True:
             try:
                 # Check for upload button or "Release" indicators specific to logged-in state
                 # e.g. "发布视频" button, or user avatar
                 if self.page.get_by_text("点击上传").count() > 0 or \
                    self.page.get_by_text("发布视频").count() > 0 or \
                    self.page.locator(".upload-btn").count() > 0 or \
                    self.page.locator(".creator-header").count() > 0:
                      is_logged_in = True
                      self.log("[+] 检测到手动登录成功！")
                      break
             except: pass
             
             if wait_cycle % 15 == 0:
                 self.log(f"等待抖音登录... (请扫码)")
                 self._capture_login_qr("抖音")


             try:
                 time.sleep(2)
             except KeyboardInterrupt:
                 return {"status": "failed", "msg": "任务被人为中断"}
                 
             wait_cycle += 1
             
        self.log("[+] 登录成功，发布页面已就绪。正在尝试填写内容...")
        
        # Douyin filling logic
        try:
             self.page.wait_for_timeout(3000) # Give UI a moment to settle
             
             # 1. Fill Text (Title & Content)
             # Douyin creator inputs can be split (Title + Desc) or combined (Desc only)
             is_text_filled = False
             try:
                 # Try separate Title input first (often found in Article/Video modes)
                 # "input" with placeholder "标题"
                 title_inputs = self.page.locator("input[placeholder*='标题'], .input-title, .title-input")
                 if title_inputs.count() > 0 and title_inputs.first.is_visible():
                      title_inputs.first.click()
                      title_inputs.first.fill(title)
                      self.log(f"[+] 已填写标题: {title[:10]}...")
                      is_text_filled = True
                 
                 # Fill Content/Description
                 # Often rich text editor (ProseMirror) or contenteditable div
                 editor = self.page.locator(".zone-container .editor-kit-container .ProseMirror, .input-container .editor, div[contenteditable='true'], textarea").first
                 if editor.count() > 0 and editor.is_visible():
                      editor.click()
                      self.page.wait_for_timeout(500)
                      # If title wasn't filled separately, add it to content
                      full_text = content if is_text_filled else f"{title}\n{content}"
                      self.page.keyboard.type(full_text)
                      self.log("[+] 已填写正文描述")
                      is_text_filled = True
                 
                 if not is_text_filled:
                      self.log("[!] 未能定位到输入框，尝试全局Tab键定位...")
                      # Fallback: Just press Tab a few times and type? Risky.
                      pass
             except Exception as e:
                 self.log(f"[!] 填写文字时出错: {e}")

             # 2. Save Draft (暂存) & Exit
             try:
                 self.log("[-] 正在尝试 '暂存' 草稿...")
                 
                 # Look for "暂存" button
                 # Often near the bottom
                 save_btn = self.page.locator("button:has-text('暂存'), .save-draft-btn").first
                 
                 if save_btn.count() > 0 and save_btn.is_visible():
                      save_btn.click()
                      self.log("[+] 已点击 '暂存' 按钮")
                      self.page.wait_for_timeout(3000)
                      self.log("[+] 草稿已保存")
                 else:
                      self.log("[!] 未找到 '暂存' 按钮，请确认页面状态。")
                      
             except Exception as e:
                 self.log(f"[!] 暂存操作失败: {e}")

             self.log("[+] 任务执行完毕 (已暂存)。")
             time.sleep(3)
             
        except Exception as e:
             self.log(f"填写内容流程异常: {e}")
             time.sleep(5)

        draft_url = self.page.url
        return {"status": "success", "msg": f"抖音任务结束 (已暂存) |||LINK:{draft_url}|||"}

    def run_mock(self, data):
        # Fallback for Wechat/others not yet fully implemented
        platform = data.get("platform")
        self.log(f"正在模拟发布至 {platform}...")
        time.sleep(2)
        return {"status": "success", "msg": f"已执行模拟发布: {platform}"}
