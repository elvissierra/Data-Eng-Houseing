import pandas as pd
import csv

""" 
    Capture state of badge text and hover text for POI's hours and category nearest version around/beofre June 20th
        - task of finding version before editors made updates

LOGIC:
- Read config and scrape by place ids:
- search place id
- enter poi
- 
    - Locate date before edit was made to hours or category
        - 
        - For date prior to the edit
            - locate hover text for modern_category (eg. internal- ModernCategoryConflator | direct- uuid#)

 """

 # Function to get info from badge JSON
    # Note currently requires ending on same page, may need implement into config? (would have to add alot..)
    # actually just making this do most of the heavy lifting for ML Reopen Analysis 5
    def badge_json_check(output_cols):
        global comments, output_row_list
        print("Checking badge JSON info...")
        expected_col_num = 12
        if len(output_cols) < expected_col_num:
            print(
                f"{YELLOW}\tWARNING: Less output cols provided than expected for custom logic! Only using first {len(output_cols)}...{RESET}"
            )
        elif len(output_cols) > expected_col_num:
            print(
                f"{YELLOW}\tWARNING: More output cols provided than expected for custom logic! Only using first {expected_col_num}...{RESET}"
            )
        output_list = []
        try:
            sic = pd_dict["Show In Client - Status"]["scrape"]
        except:
            warning = f"No Show In Client - Status found!"
            print(f"{YELLOW}\tWARNING: {warning}{RESET}")
            sic = ""
        print(f"sic: {sic}")
        # try:
        #     closed_date = driver.find_element(*pd_dict["Show In Client - Date"]["selector"]).text.strip()
        # except:
        #     warning = f"No Show In Client - Date found!"
        #     print(f"{YELLOW}\tWARNING: {warning}{RESET}")
        #     closed_date = ''
        # 2/11 adjustment using other input col Closure Date provided
        closed_date = other_input_dict["Closure Date"][row - start_row]
        print(f"closed_date: {closed_date}")
        closed_date_obj = datetime.strptime(closed_date, "%m/%d/%Y").date()
        # ALWAYS need to check versions tab for the closed version on said date now
        # check if need to switch tab
        if "Permanently" in sic:  # and "All" not in closed_date:
            sic = "No"
            reopen_source = "N/A"
            reopen_date = "N/A"
        else:
            # if "All" in closed_date:
            #     # need to get actual date from versions tab
            #     sic = 'No'
            #     reopen_source = "N/A"
            #     reopen_date = "N/A"
            #     version_i = 0
            #     print(f"{YELLOW}\tWARNING: No specific closed date provided! Getting from Versions tab...{RESET}")
            # else:
            sic = "Yes"
            # this not sufficient, need to check versions for latest open version
            # try:
            #     reopen_badge = pd_dict["Show In Client - Badge"]["scrape"]
            #     reopen_source = determine_source(reopen_badge)
            # except:
            #     warning = f"No Show In Client - Badge found!"
            #     print(f"{YELLOW}\tWARNING: {warning}{RESET}")
            #     reopen_source = ''
            # try:
            #     reopen_date = pd_dict["Show In Client - Date"]["scrape"]
            # except:
            #     warning = f"No Show In Client - Date found!"
            #     print(f"{YELLOW}\tWARNING: {warning}{RESET}")
            #     reopen_date = ''
            # version_i = 1
            print(
                "POI currently open! Switching to Last open version of versions tab..."
            )

        # switch
        # can this use either "kh" or "release"? when either? May need to try both if one blank?
        # vurl = f"https://apollo.geo.apple.com/p/release/{place_id}/versions"
        # vurl = f"https://apollo.geo.apple.com/p/kh/{place_id}/versions"
        # can just use current url (place details page) to avoid kh/release issue
        vurl = f"{driver.current_url}/versions"
        print(f"vurl: {vurl}")
        driver.get(vurl)
        output_row_list = handle_page_load("versions", output_row_list)
        if not valid_link:
            process_ticket(
                output_row_list,
                row,
                output_file,
                todo_dict,
                pd_dict,
                versions_dict,
                raps_dict,
                edits_dict,
                todos_tab_dict,
                ticket_start_time,
                i,
                ids_list,
                ticket_runtimes,
            )
            return
        time.sleep(1)
        # moved this outside for use by other functions
        versions_list = load_versions()
        # # should be second version? (test if reliably closed one or need to loop and match date)
        # last_closed_vlink = versions_list[version_i].find_element(*versions_dict["Last_closed"]["Version link"]["selector"]).get_attribute('href')
        # last_closed_vdate = versions_list[version_i].find_element(*versions_dict["Last_closed"]["Version header - date"]["selector"]).text
        # print(f"last_closed_vlink: {last_closed_vlink}")
        # print(f"last_closed_vdate: {last_closed_vdate}")
        # if version_i: # != 0
        #     driver.get(last_closed_vlink)
        #     time.sleep(1)  # wait for tab to load
        # else:
        #     closed_date = last_closed_vdate
        # need to loop through versions
        v_i = 0
        vdate = ""
        vnote = ""
        closed_badge = None
        relevant_vdate = ""
        # exact_date_match = False
        before_date_match = False
        first_match_vlink = None
        first_match_vname = None
        first_match_vnote = None
        first_match_vdate = None
        second_match_vlink = None
        for v_i, sic_version in enumerate(versions_list):
            # # trying to avoid odd stale element error...
            # for v_i in range(len(versions_list)):
            #     try:
            #         # Fetch version element again
            #         sic_version = versions_list[v_i]
            vlink = sic_version.find_element(
                *versions_dict["Last_closed"]["Version link"]["selector"]
            ).get_attribute("href")
            vname = sic_version.find_element(
                *versions_dict["Last_closed"]["Version header - name"]["selector"]
            ).text
            vnote = sic_version.find_element(
                *versions_dict["Last_closed"]["Version header - note"]["selector"]
            ).text
            vdate = sic_version.find_element(
                *versions_dict["Last_closed"]["Version header - date"]["selector"]
            ).text
            print(f"vlink: {vlink}")
            print(f"vname: {vname}")
            print(f"vnote: {vnote}")
            print(f"vdate: {vdate}")
            # convert date to object for comparison
            vdate_obj = datetime.strptime(vdate, "%Y-%m-%d %I:%M %p %Z").date()
            relevant_vdate = vdate_obj.strftime("%m/%d/%Y")
            if v_i == 0 and sic == "Yes":
                # reopen_source = vname
                reopen_source = vnote
                # reopen_date = vdate
                reopen_date = vdate_obj.strftime("%m/%d/%Y")
            # moved this condition up to go to if no matching version and allow overwriting first_match_vlink
            # Discovered given closure date may be earlier than the actual version date where said closure was first applied, can use <= accordingly
            # changed to within a day before, actually seems need to do 2 weeks
            # print(f"date compare: {first_match_vlink}, {closed_date_obj - timedelta(days=14)}, {vdate_obj}, {closed_date_obj}")
            print(f"date compare: {vdate_obj}, {closed_date_obj + timedelta(days=1)}")
            # if not first_match_vlink and (closed_date_obj == vdate_obj - timedelta(days=1)):
            if not first_match_vlink and (
                closed_date_obj - timedelta(days=14)
                <= vdate_obj
                <= (closed_date_obj - timedelta(days=1))
            ):
                # print(f"Version #{v_i+1} found by closed date {closed_date}!")
                print(
                    f"{YELLOW}\tWARNING: Version found with closed date {relevant_vdate} within 2 weeks before{RESET}"
                )
                if v_i > 0:
                    print(f"Opening...")
                    driver.get(vlink)
                    time.sleep(1)  # wait for tab to load
                    before_date_match = True
                # else already open
                break
            elif vdate_obj == closed_date_obj:
                if first_match_vlink:
                    print(
                        f"2nd version #{v_i + 1} found with same closed date {relevant_vdate}"
                    )
                    second_match_vlink = vlink
                    # reassign as first_match variables
                    vlink = first_match_vlink
                    vname = first_match_vname
                    vnote = first_match_vnote
                    vdate = first_match_vdate
                    # recalc these
                    vdate_obj = datetime.strptime(vdate, "%Y-%m-%d %I:%M %p %Z").date()
                    relevant_vdate = vdate_obj.strftime("%m/%d/%Y")
                    if v_i > 0:
                        print(f"Opening 1st version...")
                        print(f"first_match_vlink: {first_match_vlink}")
                        driver.get(first_match_vlink)
                        time.sleep(1)  # wait for tab to load
                    # else already open
                    break
                else:
                    print(f"Version #{v_i + 1} found with closed date {relevant_vdate}")
                    # exact_date_match = True
                    first_match_vlink = vlink
                    first_match_vname = vname
                    first_match_vnote = vnote
                    first_match_vdate = vdate
                    continue
            # also need condition for day after, but want same day to overwrite first_date_match...
            elif vdate_obj == closed_date_obj + timedelta(days=1):
                print(
                    f"Version #{v_i + 1} found with closed date {relevant_vdate} within a day after"
                )
                # exact_date_match = True
                first_match_vlink = vlink
                first_match_vname = vname
                first_match_vnote = vnote
                first_match_vdate = vdate
                continue
            elif first_match_vlink:
                print(
                    f"{YELLOW}\tWARNING: No valid version found matching closed date {closed_date}{RESET}"
                )
                # reassign as first_match variables
                vlink = first_match_vlink
                vname = first_match_vname
                vnote = first_match_vnote
                vdate = first_match_vdate
                # recalc these
                vdate_obj = datetime.strptime(vdate, "%Y-%m-%d %I:%M %p %Z").date()
                relevant_vdate = vdate_obj.strftime("%m/%d/%Y")
                if v_i > 0:
                    print(f"Opening version found within day after...")
                    driver.get(first_match_vlink)
                    time.sleep(1)  # wait for tab to load
                break
        # last resort to get examples that may have relevant version more than a day after etc.
        if not first_match_vlink and not before_date_match:
            print(
                f"{YELLOW}\tWARNING: No valid versions found! Assuming top-most applies...{RESET}"
            )
            versions_list = load_versions(page_switched=False)
            vname = (
                versions_list[0]
                .find_element(
                    *versions_dict["Last_closed"]["Version header - name"]["selector"]
                )
                .text
            )
            vnote = (
                versions_list[0]
                .find_element(
                    *versions_dict["Last_closed"]["Version header - note"]["selector"]
                )
                .text
            )
            vdate = (
                versions_list[0]
                .find_element(
                    *versions_dict["Last_closed"]["Version header - date"]["selector"]
                )
                .text
            )
            # recalc these
            vdate_obj = datetime.strptime(vdate, "%Y-%m-%d %I:%M %p %Z").date()
            relevant_vdate = vdate_obj.strftime("%m/%d/%Y")

        # is finding first instance of date sufficient or need to at least make sure sic=No?
        # need to at least warn as may be fatal error
        # time.sleep(10)
        try:
            # closed_status = driver.find_element(*pd_dict["Show In Client - Status"]["selector"]).text.strip()
            # this didn't work for some reason...
            # print(f"pd_dict['Show In Client - Status']['selector']: {pd_dict['Show In Client - Status']['selector']}")
            # closed_status = WebDriverWait(driver, 40).until(EC.presence_of_element_located(*pd_dict["Show In Client - Status"]["selector"])).text.strip()
            # closed_status = WebDriverWait(driver, 40).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[title^=Show] + div .col-value"))).text.strip()
            # this way actually gets all closures if multiple like Current and Other (may need to reconsider config or general Closure scrape handling too)
            closed_status = (
                WebDriverWait(driver, 40)
                .until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "[title^=Show] + div .col")
                    )
                )
                .text.strip()
            )
        except:
            warning = f"No Show In Client - Status found!"
            print(f"{YELLOW}\tWARNING: {warning}{RESET}")
            closed_status = ""
        print(f"closed_status: {closed_status}")
        # use latest closed version as backup method in this case, go back? only if switched?
        # if "permanently" not in closed_status:
        # this way accounts for temporarily too
        if "Closed" not in closed_status:
            # warning = f"Version #{v_i+1} found by closed date {closed_date} isn't closed as expected!"
            warning = (
                f"Version found with date {relevant_vdate} isn't closed as expected!"
            )
            # print(f"{RED}\tERROR: {warning} May need to try next version #{v_i+2}.{RESET}")
            print(f"{YELLOW}\tWARNING: {warning} Trying diff version...{RESET}")
            comments = add_comment(comments, warning)
            # how to always know whether to go to prev or next version?
            # if date was exact match go next otherwise go back?
            # if exact_date_match:
            if second_match_vlink:
                print(f"Going to next version...")
                # if v_i > 0:
                #     versions_list = load_versions()
                # print(f"len(versions_list): {len(versions_list)}")
                # v_adj = v_i + 1
                # just this now because would have already advanced 1 version?
                v_adj = v_i
                # vlink = versions_list[v_adj].find_element(*versions_dict["Last_closed"]["Version link"]["selector"]).get_attribute('href')
                print(f"second_match_vlink: {second_match_vlink}")
                driver.get(second_match_vlink)
                time.sleep(1)  # wait for tab to load
            else:
                # if v_i > 0: # if first version it would have to go next
                print(f"Going back to previous version...")
                driver.back()
                time.sleep(1)  # wait for tab to load
                v_adj = v_i - 1
            # recapture versions_list to prevent stale element
            # print(f"v_i: {v_i}")
            versions_list = load_versions()
            # have to recapture these variables too
            # vlink = versions_list[v_i-1].find_element(*versions_dict["Last_closed"]["Version link"]["selector"]).get_attribute('href')
            vname = (
                versions_list[v_adj]
                .find_element(
                    *versions_dict["Last_closed"]["Version header - name"]["selector"]
                )
                .text
            )
            vnote = (
                versions_list[v_adj]
                .find_element(
                    *versions_dict["Last_closed"]["Version header - note"]["selector"]
                )
                .text
            )
            vdate = (
                versions_list[v_adj]
                .find_element(
                    *versions_dict["Last_closed"]["Version header - date"]["selector"]
                )
                .text
            )
            # print(f"vlink: {vlink}")
            print(f"vname: {vname}")
            print(f"vnote: {vnote}")
            print(f"vdate: {vdate}")
            # convert date to object for comparison
            vdate_obj = datetime.strptime(vdate, "%Y-%m-%d %I:%M %p %Z").date()
            relevant_vdate = vdate_obj.strftime("%m/%d/%Y")
            try:
                # closed_status = driver.find_element(*pd_dict["Show In Client - Status"]["selector"]).text.strip()
                # this didn't work for some reason...
                # print(f"pd_dict['Show In Client - Status']['selector']: {pd_dict['Show In Client - Status']['selector']}")
                # closed_status = WebDriverWait(driver, 40).until(EC.presence_of_element_located(*pd_dict["Show In Client - Status"]["selector"])).text.strip()
                # closed_status = WebDriverWait(driver, 40).until(EC.presence_of_element_located((By.CSS_SELECTOR,"[title^=Show] + div .col-value"))).text.strip()
                # this way actually gets all closures if multiple like Current and Other (may need to reconsider config or general Closure scrape handling too)
                closed_status = (
                    WebDriverWait(driver, 40)
                    .until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "[title^=Show] + div .col")
                        )
                    )
                    .text.strip()
                )
            except:
                warning = f"No Show In Client - Status found!"
                print(f"{YELLOW}\tWARNING: {warning}{RESET}")
                closed_status = ""
            print(f"closed_status: {closed_status}")
            # use latest closed version as backup method in this case, go back? only if switched?
            # if "permanently" not in closed_status:
            # this way accounts for temporarily too
            if "Closed" not in closed_status:
                # decided to exclude version number from warning outputs at least since numbered by SIC-filtered versions only could confuse
                warning = f"Version found with date {relevant_vdate} isn't closed as expected!"
                print(f"{RED}\tERROR: {warning}{RESET}")
                comments = add_comment(comments, warning)
        if "temporarily" in closed_status:
            warning = f"Version found with date {relevant_vdate} has temporary closure!"
            print(f"{YELLOW}\tWARNING: {warning}{RESET}")
            comments = add_comment(comments, warning)
        # 1 Closure Date
        output_list.append(closed_date)
        # 2 Source of Closure
        try:
            closed_badge = driver.find_element(
                *pd_dict["Show In Client - Badge"]["selector"]
            )
            closed_badge_txt = closed_badge.text.strip()
            closed_source = determine_source(closed_badge_txt)
        except:
            warning = f"No Show In Client - Badge found!"
            print(f"{YELLOW}\tWARNING: {warning}{RESET}")
            closed_source = ""
        print(f"closed_source: {closed_source}")
        output_list.append(closed_source)
        badge_hover_txt = ""
        if closed_source == "Editor":
            # Open the sic badge JSON for rest
            try:
                # could make this a proper config option later..
                closed_JSON_link = driver.find_element(
                    By.CSS_SELECTOR, "[title^=Show] + div a"
                ).get_attribute("href")
            except:
                warning = f"No closed JSON link found!"
                print(f"{YELLOW}\tWARNING: {warning}{RESET}")
                comments = add_comment(comments, warning)
                closed_JSON_link = ""
                closed_ttype = ""
                closed_tclient = ""
                wayback_ow_used = ""
                closed_notes = ""
            if closed_JSON_link:
                driver.get(closed_JSON_link)
                time.sleep(1)
                # get "notes" from JSON
                print("Getting notes from JSON...")
                time.sleep(1)
                # Try to load JSON data
                try:
                    raw = (
                        WebDriverWait(driver, 30)
                        .until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "code"))
                        )
                        .text.strip()
                    )
                except:
                    print(
                        f"{YELLOW}\tWARNING: JSON not loading, trying refresh...\n{RESET}"
                    )
                    try:
                        # Refresh page and try again
                        driver.refresh()
                        time.sleep(1)
                        raw = (
                            WebDriverWait(driver, 30)
                            .until(
                                EC.presence_of_element_located(
                                    (By.CSS_SELECTOR, "code")
                                )
                            )
                            .text.strip()
                        )
                    except Exception as e:
                        error_type = type(e).__name__
                        message = str(e)
                        print(
                            f"{RED}\tERROR: Could not load JSON due to error: {error_type}, report:\n{message}! Exiting script.\n{RESET}"
                        )
                        traceback.print_exc()
                        # sys.exit()
                        return
                data = json.loads(raw)
                print(f"JSON data:\n{data}")
                if "notes" in data:
                    closed_notes = data["notes"]
                    # check notes
                    match = re.search(r"(?<=1\.\s)([^-]+)", closed_notes)
                    closed_tclient = ""
                    if match:
                        closed_ttype = match.group(1).strip()  # Strip to remove any leading/trailing spaces
                    elif "rdar://" in closed_notes:
                        warning = f"Appears radar edit without ticket!"
                        print(f"{YELLOW}\tWARNING: {warning}{RESET}")
                        comments = add_comment(comments, warning)
                        closed_ttype = "N/A"
                        closed_tclient = "N/A"
                        wayback_ow_used = ""
                        # also fix previously set closed_source
                        output_list[-1] = "Radar"
                    elif "apollo.geo.apple.com" in closed_notes:
                        warning = f"Appears POI Other (Customer Outreach) ticket!"
                        print(f"{YELLOW}\tWARNING: {warning} Considering Jana{RESET}")
                        comments = add_comment(comments, warning)
                        closed_ttype = "POI Other (Customer Outreach)"
                    else:
                        warning = f"No closed ticket type found!"
                        print(f"{YELLOW}\tWARNING: {warning}{RESET}")
                        comments = add_comment(comments, warning)
                        closed_ttype = ""
                    if (
                        "POI Change" in closed_ttype
                        or "POI Remove" in closed_ttype
                        or "POI Other" in closed_ttype
                    ):
                        closed_tclient = "Jana"
                    elif not closed_tclient:
                        closed_tclient = "Gemini"
                    try:
                        ow_urls = pd_dict["URL - URL"]["scrape"]
                    except:
                        warning = f"No URL - URL found!"
                        print(f"{YELLOW}\tWARNING: {warning}{RESET}")
                        ow_urls = []
                    if closed_ttype != "N/A":
                        wayback_ow_used = "No"
                        if ow_urls:
                            for ow_url in ow_urls:
                                if (
                                    ow_url in closed_notes
                                    and "web.archive" in closed_notes
                                ):
                                    wayback_ow_used = "Yes"
                                    break
                else:
                    warning = f"'notes' field not found in JSON!"
                    print(f"{YELLOW}\tWARNING: {warning}{RESET}")
                    comments = add_comment(comments, warning)
                    closed_notes = ""
                    closed_ttype = ""
                    closed_tclient = ""
                    wayback_ow_used = ""
            # # go back to page for other custom logics after?
            # driver.back()
            # time.sleep(1)
        else:
            warning = f"Non-Editor source/no ticket for {closed_date} closure!"
            print(f"{YELLOW}\tWARNING: {warning} Setting outputs accordingly...{RESET}")
            comments = add_comment(comments, warning)
            closed_notes = "N/A"
            # closed_ttype = 'N/A'
            closed_ttype = vnote
            closed_tclient = "N/A"
            wayback_ow_used = ""
            if closed_badge:
                badge_hover_txt = closed_badge.get_attribute("title")
        # 3 Type (copy/paste)
        print(f"closed_ttype: {closed_ttype}")
        output_list.append(closed_ttype)
        # 4 Client
        print(f"closed_tclient: {closed_tclient}")
        output_list.append(closed_tclient)
        # 5 Reopened?
        output_list.append(sic)
        # 6 Reopen Source
        print(f"reopen_source: {reopen_source}")
        output_list.append(reopen_source)
        # 7 Reopen Date
        print(f"reopen_date: {reopen_date}")
        output_list.append(reopen_date)
        # 8 Closed After 2/13/24?
        # closed_date_obj = datetime.strptime(closed_date, '%Y-%m-%d %I:%M %p %Z')
        # Define the date of Feb 13th, 2024
        after_date = datetime(year=2025, month=6, day=1).date()
        if closed_date_obj > after_date:
            closed_after = "Yes"
        else:
            closed_after = "No"
        print(f"closed_after: {closed_after}")
        output_list.append(closed_after)
        # 9 Wayback & Official Website ONLY?
        print(f"wayback_ow_used: {wayback_ow_used}")
        output_list.append(wayback_ow_used)
        # 10 raw editor who closed notes
        print(f"closed_notes: {closed_notes}")
        output_list.append(closed_notes)
        # 11 relevant version date (converted to proper matching string format)
        # if vdate:
        if relevant_vdate:
            # relevant_vdate_obj = datetime.strptime(vdate, '%Y-%m-%d %I:%M %p %Z').date()
            # relevant_vdate = relevant_vdate_obj.strftime("%m/%d/%Y")
            if vdate_obj > closed_date_obj:
                warning = f"Relevant version date {relevant_vdate} AFTER given closure date {closed_date}!"
                print(f"{YELLOW}\tWARNING: {warning}{RESET}")
                comments = add_comment(comments, warning)
            elif vdate_obj < closed_date_obj:
                warning = f"Relevant version date {relevant_vdate} BEFORE given closure date {closed_date}!"
                print(f"{YELLOW}\tWARNING: {warning}{RESET}")
                comments = add_comment(comments, warning)
        # else:
        #     relevant_vdate = ''
        print(f"relevant_vdate: {relevant_vdate}")
        output_list.append(relevant_vdate)
        # 12 SIC badge hover text
        print(f"badge_hover_txt: {badge_hover_txt}")
        output_list.append(badge_hover_txt)

        # output
        for output_col, output in zip(output_cols, output_list):
            set_output(output, output_col)
