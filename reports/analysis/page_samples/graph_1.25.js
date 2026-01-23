var STLINPMSG = 'Type in comma separated alloy names, use autosuggest for assist',
    DFPX = 'Type in';

/**
 global func for events, since directly setting suggestionsObj.hide() on event looses "this" and creating anonymous functions
 separately for add and remove event wont' remove anything because anonymous functions will be different  
*/
function hideSuggestions()
{
   suggestionsObj.hide();
}

/**
 * detect steel names with alternates i.e. name (altnames) remove everything
 * except for the name. Also, replaces &nbsp; with normal spaces again.
 * 
 * @param inStr
 *           return value - steel name
 */
function lk2SgV(inStr)
{
     var parenIdx = inStr.lastIndexOf('(');
     if ( parenIdx >= 0 )
     {
        return inStr.substring(0,parenIdx);
     }

     return inStr;
}

var GraphCtl=
{
   defSz: '2',
   elemDiv: 'filterElements',
   cp:  'cpanel',
   nrIds: [],
   elements: [ 'C', 'Cr', 'Co', 'Cu', 'Mn', 'Mo', 'N', 'Nb', 'Ni', 'P', 'S', 'Si', 'W', 'V'],
   defElements: ["C", "Cr", "Co", "Mn", "Mo", "Si", "W", "V"],
   stgDlg: null,

   init: function()
   {
      var gct = GraphCtl,
          zkevt = zkEvent,
          nmCtl, e, szv, d, stlTable;
      
      if ( $(gct.cp) )
      {
         if ( !zkTltip.tip )
            zkTltip.init();
         if ( $('hrn').checked )
            gct.shRefs();
         
         stlTable = $('steelData');
         if ( stlTable )
            stlTable.style.visibility = "visible";
         
         gct.adjustCpanel();
         gct.initRIds();
         gct.setupElements();
         
         zkevt.add( document, 'keydown', gct.kbHnd, true );
         zkevt.add($('nm'), 'keyup', gct.onKeyUp, false );
         
         zkevt.add($('hrn'), 'click', gct.shRefs, false );
         zkevt.add($('grStgs'), 'click', gct.showMore, false );
         zkevt.add($('submit'), 'click', gct.onSubmit, false );
         
         zkevt.add($('lastBtn'), 'mouseover', gct.showHelp, false);
         zkevt.add($('lastBtn'), 'mouseout', gct.hideHelp, false);
         zkevt.add($('kbdshortslnk'), 'click', gct.showKbdHlp, false);
         
         nmCtl = $('nm');
         zkevt.add(nmCtl, 'focus', gct.srchFc, false);
         zkevt.add(nmCtl, 'blur', gct.srchBl, false);
         
         if ( !nmCtl.value )
         {
            nmCtl.value = STLINPMSG;
         }
         else
         {
            // display notification message if some alloys were disabled
            if ( rqIt > actIt )
            {
               e = $('sz');
               szv = e.options[e.selectedIndex].text;// current size
               d = new zDlgAlrt(zDlgAlrt.Error);
               d.setTitle('Insufficient space to display complete comparison graph!');
               d.setContent("<div style='text-align:left'>Graph size " + szv +  
               " is insufficient to compare " + rqIt + " alloys, " + (rqIt - actIt) + " alloys were disabled, you can:<br />" +
               "1) Increase graph size from <em>Settings</em> menu;<br />" + 
               "2) Reduce the number of the displayed components <em>Settings</em> menu.</div>");
               gct.errdlg = d;
               posCenter(gct.errdlg.container);
               gct.errdlg.show();
            }
         }
      }

      if ( vectData )
      {
         zkevt.add( $('graphImg'), 'mousemove', zkTltip.onImgMouseMove );
      }
   },

   // default keyboard handler for general graph object keyboard entries
   kbHnd: function(e)
   {

      e = zkEvent.setTgt(e);

      switch ( e.keyCode)
      {
        case 71:// alt+G display settings dialog
            if ( e.altKey )
                GraphCtl.showMore();
        break;
        
        case 73:// Alt+I show/hide ref names
           if ( e.altKey )
              GraphCtl.shRefs();
           break;

        case 221:// Alt+] select input text
           if ( e.altKey )
           {
              var inp = $('nm');
              inp.focus();
              inp.select();
           }
           break;
           
        case keyEnter:
           if ( suggestionsObj !== null && suggestionsObj.isVisible() )
              suggestionsObj.setSelected();
           e.preventDefault();
           GraphCtl.onSubmit();      
         break;

         default:
            return true;

      }
      return false;
   },
   
   // keyboard handler for the steel names input box handles most of the valid key
   // input,
   // has to be in keyup, which is when input actually has the new key added to its
   // value
   onKeyUp: function (e)
   {
   
      switch(e.keyCode)
      {
         case keyDown://Arrow down select next
         case keyUp://Arrow up select prev
         case keyEscape:
         case keyTab:
         case keyEnter:
         case keyRight:
            return false;
         
         default:
            break;
      }
   
      return GraphCtl.getSuggestions();
   },
   
   
   getSuggestions: function()
   {
      var sgObjEdit = $('nm');

     if ( sgObjEdit.value )
     {
        var val = sgObjEdit.value,
        lastComa = val.lastIndexOf(',');
        
        // we're trying to find what's after last comma if any.             
        if (lastComa !== -1)
        {
           val = val.substring(lastComa+1, val.length);
        }
     
        if ( val )
        {
           val = val.replace(/%/g,'');
           
           if ( val && val !== '*')
           {      
              val = val.replace(/\*/g,'%');
              val = htmlscEc(val);
              var onReady = function(req)
              {
                 var valArray = null;
                 if ( req.responseText )
                 {
                    valArray = JSON.parse(req.responseText);
                 }
                 
                 if (valArray !== null && valArray.length > 0)
                    suggestionsObj.show(sgObjEdit, valArray);
                 else
                    if (suggestionsObj.isVisible())
                       suggestionsObj.hide();
                 
              };
           
              var queryString = "php/stlajax.php?val=" + encodeURIComponent(val);
   //           console.log(queryString);
              ajaxGetReq(queryString, onReady);
           }
        }
     }
      
   },
   
   showKbdHlp: function()
   {
      var gct = GraphCtl,
          dlg,
          content;
      
      if ( !gct.kbdHlp )
      {
         dlg = new zDlgAlrt(zDlgAlrt.Info);
         dlg.setTitle('Keyboard Shortcuts');
         content = $('kbdshorts');
         content.style.display = "block";
         dlg.setCntObj(content);
         gct.kbdHlp = dlg;
      }
      
      posCenter(gct.kbdHlp.container);
      gct.kbdHlp.show();
      
   },
   
   srchFc: function(e)
   {
      var o = zkEvent.getTgt(e);
      if ( o.value.startsWith(DFPX) )
         o.value = '';
   },

   /**
    * when loosing focus, check if it is still empty and set the text.
    * 
    * @param e
    */
   srchBl: function(e)
   {
      var o = zkEvent.getTgt(e);
      if ( o.value === null || o.value.length === 0 )
      {
         o.value = STLINPMSG;
         clrArray(GraphCtl.nrIds);
      }
   },
   
   
   // initialize rowid array from the query string, if there was ni parameter
   initRIds : function()
   {
      var nmCtl = decodeURIComponent(getQryParam('nm')),
          ni = getQryParam('ni'), i;
      
      if ( ni && nmCtl )
      {
         var nms = nmCtl.split(','),
             nis = ni.split(','),
             nid;
         // go through names and try to match id for each, if there are not
         // enough ids, set the rest of the name ids to null
         for ( i = 0; i < nms.length; i++ )
         {
            nid = null;
            if ( i < nis.length )
               nid = nis[i];
            GraphCtl.nrIds.push( {name:nms[i], nid:nid, namePos:i} );
         }
      }
   },
   
  adjustCpanel : function()
  {
      var c = $(GraphCtl.cp);
      if ( c )
      {
         var e = $('nm'),
             h = $('lastBtn');
         // subtract extra 4 for input box borders
         e.style.width = e.offsetWidth + (c.offsetLeft + c.offsetWidth - h.offsetLeft - h.offsetWidth )-15 + 'px';
         c.style.visibility='visible';
      }
  },

   shRefs : function()
   {
      var rule = getCSS(3, '.' + 'stlGrpNm', false);
      if (rule)
      {
         var tp = zkTltip.tipProps,
             rs = rule.style;
         
         if (rs.display === 'none')
         {
            rs.display = '';
            tp.qryParam = 'nn';
         }
         else
         {
            rs.display = 'none';
            tp.qryParam = 'in=1&' + tp.qryParam;
         }
      }
   },

   
   // retreives the input parameters and
   onSubmit: function()
   {
     var el = '',
     ecVal = $('nm').value,//text value of the search edit control
     i, lastComa,
     ni = [],
     bHasId = false,
     gct = GraphCtl;
     
     
     if ( !ecVal || ecVal.length === 0 || ecVal.startsWith(DFPX))
     {
         if ( gct.errdlg === null )
        {
           var d = new zDlgAlrt(zDlgAlrt.Error);
           d.setTitle('Error!');
           d.setContent("You must specify at least one alloy to build the graph!");
           gct.errdlg = d;
        }
        posCenter(gct.errdlg.container);
        gct.errdlg.show();
       return;
     }
      
     lastComa = ecVal.lastIndexOf(',');
     //if coma is the last character in the string, remove it
     if (lastComa === ecVal.length-1 )
     {
        ecVal = ecVal.substring(0,lastComa);
        $('nm').value = ecVal;
     }     
     
      if ( gct.nrIds.length > 0 )
      {         
         var snms = ecVal.split(','),
             nrids = gct.nrIds,
             nl = nrids.length,
             snmLen = snms.length;
         // find name record ids for alloys
         for ( i = 0; i < snmLen; i++ )
         {
           var curNi = '';// set to empty rowid, so that php can determine to
           // use record CID as a criteria in the case of mixed input, i.e.
           // some records have rowids, some don't. that happens because the user
           // manually typed in the alloy name and didn't pick it form the suggest box
            
            for ( j = 0; j < nl; j++ )
            {
               if ( nrids[j] )
               {// this is the rowid for the alloy name
                  var sname = htmlsceDc( lk2SgV( nrids[j].name.toLowerCase() ) );
                  if ( sname === snms[i].toLowerCase() )
                  {
                     curNi = nrids[j].nid;
                     // set the object to null to void repeating same ids for
                     // the alloys with the same name
                     nrids[j] = null;
                     bHasId = true;// set the flag, we got at least one rowid
                     break;
                  }
               }
            }
            ni.push(curNi);
         }
      }
      
      var ge = gct.elements,
          gel = ge.length;
      
      for ( i=0; i < gel; i++)
      {
         var chk = $(ge[i]);
         if ( chk && chk.checked )
         {
            el += chk.value + ',';
         }
      }

      gct.formUrl( bHasId, ni, el, ecVal );

   },
   
   formUrl: function( bHasId, ni, el, nmv )
   {
      var szElem, szVal, dstRef;
      szElem = $('sz');
      szVal = szElem.options[szElem.selectedIndex].value;

      dstRef = 'steelgraph.php?nm=' + encodeURIComponent(nmv);
      
      if ( bHasId )
         dstRef += '&ni=' + ni.join(',');

      if ( szVal !== GraphCtl.defSz)
          dstRef += '&sz=' + szVal;

      if (el.length !== 0)
      {
         // if the string is ending with , remove it.
         if ( el.charAt(el.length-1) === ',')
            el = el.substring(0,el.length-1);

         dstRef += '&el=' + encodeURIComponent(el);
      }

      if ( $('avg').checked === true)
          dstRef += '&avg=1';

      var t = ( $('hrn').checked ) ? '1' : '0';
      dstRef += '&hrn=' + t;
      
      dstRef += '&gm=' + $('gm').selectedIndex;
       // finally build the query string.
//      console.log("Final Build URL - " + dstRef);
      document.location.href = dstRef;      
   },

   setupElements: function()
   {
      var el = decodeURIComponent(getQryParam('el'));
      var elIds = null;
      if ( el !== null && el.length > 0)
         elIds = el.split(',');

      GraphCtl.chkEl(elIds, true);
   },

   clearAll: function()
   {
      GraphCtl.chkEl(GraphCtl.elements, false);
   },

   selectAll: function()
   {
      GraphCtl.chkEl(GraphCtl.elements, true);
   },

   selectDefaults: function()
   {
	   GraphCtl.chkEl(GraphCtl.elements, false);
	   GraphCtl.chkEl(GraphCtl.defElements, true);
   },

   chkEl: function(elIds, value)
   {
     if( elIds !== null)
     {
        var chk,
        len = elIds.length;
         do
         {
            chk = $(elIds[len]);
            if ( chk )
               chk.checked = value;
         } while ( len-- );
     }
   },

   showMore: function()
   {
      if ( GraphCtl.stgDlg === null )
      {
         var d = new zDlgConfirm(zDlgAlrt.Warning, GraphCtl.onSubmit, null, 'Build', null);
         d.setTitle("Advanced Options");
         var sd = $(GraphCtl.elemDiv);
         sd.style.visibility = "inherit";
         d.setCntObj(sd);
         GraphCtl.stgDlg = d;
      }
      // center settings dialog in parent form top line
      var f = $('formDiv');
      var p = getPgOffsets(f);
      GraphCtl.stgDlg.moveTo(p.x + f.offsetWidth/2,p.y);
      GraphCtl.stgDlg.show();
   },

   showHelp: function()
   {
      $('sm_mnuhlp').style.visibility = "visible";
   },

   hideHelp: function()
   {
      $('sm_mnuhlp').style.visibility = "hidden";
   }
};

zkTltip.req = null;
zkTltip.lastVal = null;

zkTltip.qryParam = function(qryParam, tgt)
{
   if ( tgt )
   {
     var cls = zkTltip.getTipCls(tgt.className);
     // remove stl form the class and return it, because steel names are
      // prefixed with stl as secodn class name
     return cls.substring(3);
   }
   return null;
};

// val here is what zkTltip.qryParam returns, i.s. Steel name, use it as a title
// also
// special case is val Gdata, where we pretty much fake ajax request response
// and display graph element hover data.
zkAjaxReqFn = function( queryString, val )
{
   var ztip = zkTltip; 
   if ( ztip.req && ztip.lastVal !== val )
   {
      // on abort ajax sets ready state to 4, making it impossible to
      // distinghish between abort and normal completion.
      // easiest way to solve this is to remove readystate handler.
      ztip.req.onreadystatechange = function(){};
      ztip.req.abort();
   }
   
   ztip.req = createAjaxReq();
   if ( ztip.req )
   {
      ztip.req.onreadystatechange = function()
      {
         if( ztip.req && ztip.req.readyState === 4 )
         {
            ztip.responseReady(ztip.req, val);
         }
      };
      ztip.lastVal = val;
      ztip.req.open("GET", "php/stlajax.php?" + queryString, true);
      ztip.req.send(null);
      return true;
   }
   return false;
};

// stl is the original name retreived from the mouseover target
zkTltip.responseReady = function( req, stl )
{
   var rspObj,
       status = req.status;
   
   if ( status === 200 && req.responseText )
      rspObj = JSON.parse(req.responseText);
   else
      rspObj = { ttl:'Error!', msg:'No data available!'};
   req.onreadystatechange = function(){};
   zkTltip.respRecd = true;
   zkTltip.genTipBody(rspObj.msg, rspObj.ttl, 'stl' + stl, true);
   zkTltip.posFn( null, zkTltip.tpSrc);
   zkTltip.req = null;
};

zkTltip.zkOnHide = function()
{// abort request in progress if we have to hide
   if ( zkTltip.req )
   {
      var ztip = zkTltip;
      ztip.req.onreadystatechange = function(){};
      ztip.req.abort();
      ztip.resetReqFlags();
  }
};

// graph specific tip builder function
zkTltip.ppGrTip = function(txt, ttl,htmlId)
{
   ttl = ttl || 'Please Wait';
   
   this.tip.style.maxWidth = htmlId === 'gd' ? '250px' : '600px';
      
   var msg = '<div id="graphTipDiv" >' +
     '<div class="graphTipTtl">'  + 
     ttl + '</div>' +
     '<div class="stkCont">' + txt + '</div></div>';

   return msg;
};

// remove tip, no delay, i.e. set tooltip delay to 0, call remove and restore
// old value for other tips
zkTltip.rmvTipND = function (e)
{
   if ( zkTltip.activeImgTip >= 0 )
   {
      var o = zkTltip.dlyHide;
      zkTltip.dlyHide = 0;
      zkTltip.rmvTip(e);
      zkTltip.dlyHide = o;
      zkTltip.activeImgTip = -1;
   }
};

/**
 * Main functoin handlig tooltips over the image. On mousemove saves current
 * coordinates in cmx and cmy. Coordinates include page scroll offset if any.
 * Then current position is analyzed by getGRHoverData and if match rect with
 * text is found tip is displayed
 */
zkTltip.onImgMouseMove = function (e)
{
    var tgt = zkEvent.getTgt(e);
    // if we're hovering over the graph image, ignore mouseover event, we'll
      // display tips on mousemove.
   if ( tgt.id === 'graphImg' )
   {
      cmx = zkTltip.getMEPosX(e);
      cmy = zkTltip.getMEPosY(e);
      if ( zkTltip.getGRHoverData(e, tgt) )
         zkTltip.posAtSrc(e,tgt);
   }
};

/**
 * Receives mousemove event and image as a target. THe page contains vectData
 * array which is generated by steelgraph.php containing rects and accompanying
 * message with title. Current mouse position is checked against all rects and
 * if the point is contained by one of the rects in vectData tip is displayed
 * using ttl and msg for the matching rect. zkTltip.process displays the tip,
 * after that attach an event to mouseout to kill the tip if the mouse goes out
 * of the image object. If no match is found, call remove tip funciton to remove
 * any existing tips.
 */
zkTltip.getGRHoverData = function(e, tgt)
{
   // calculate mouse position relative to image top left, i.e. 0,0 of the image
   var img = $('graphImg'),
       imgOffset = getPgOffsets( img ),        // first get image offset in
                                                // page
       sc = getElScroll( img ),         // get image scroll position
       x = cmx - imgOffset.x + sc.x,          // subtract scroll x, this is
                                                // needed because image
       i, o, oRect, l,                         // can be scrolled horizontally
                                             // inside the parent
       y = cmy - imgOffset.y;                 // div
   
   
   zkTltip.respRecd = true;
   l = vectData.length;
   for ( i = 0; i < l; i++ )
   {
      o = vectData[i];
      oRect = o.rect;
      if ( x >= oRect.x && x <= oRect.x + oRect.w && y >= oRect.y && y <= oRect.y + oRect.h )
      {
         if ( zkTltip.activeImgTip !== i )
         {
            zkTltip.process(e, tgt, o.text, null, o.ttl, 'gd');
               if ( window.attachEvent )
                   zkEvent.remove( tgt, 'mouseout', zkTltip.rmvTipND);
            zkEvent.add( tgt, 'mouseout', zkTltip.rmvTipND);
            zkTltip.activeImgTip = i;
         }
         return true;
      }
   }
   zkTltip.rmvTipND(e);
   return false;
};

zkTltip.tipProps = {
         srcType : 'qryParam',
         ctSrc : 'ajax',
         qryParam : 'nn',
         sticky : false,
         bShowCB : false,
         posFn : zkTltip.posAtSrc,
         objPreProc : zkTltip.ppGrTip
 };


// remove links from prev. query from the sgDiv.
SuggestionsObj.prototype.cleanSgDiv = function()
{
   var dl = this.divLinks,
       llkDiv = this.lkDiv,
       linky;
   
   if (llkDiv && dl )
   {
      for (linky in dl)
      {
         if ( dl.hasOwnProperty(linky) )
         {
            llkDiv.removeChild(dl[linky]);
         }
      }
      this.divLinks = null;
      llkDiv.style.height = '';
   }
};

SuggestionsObj.prototype.hide = function()
{
   if ( this.sgDiv )
   {
      this.sgDiv.style.visibility = 'hidden';
      $('stlScbContainer').style.visibility = 'hidden';
      zkEvent.remove( document, 'mouseup', hideSuggestions, false);
      this.cleanSgDiv();
   }
};

SuggestionsObj.prototype.show = function showSuggestions(obj, valArray)
{
// setup listeners
   var inst = this,
       pos = DOM.getPos(obj),
       ceStl,// curent sgdiv style
       doc = document,
       zkevt = zkEvent,
       frag, linky, scStl;

   this.sgElem = obj;// element for which we need suggestions
   this.curSel = -1;// current selection in the suggestions
   this.sgDiv = $(sgDivId);
   this.nrIds = valArray;
   var scb = $('stlScbContainer');
   
   if (this.sgDiv === null)
   {
      this.sgDiv = DOM.ce("div", {className:"suggestDiv", id:sgDivId});
      doc.body.appendChild(this.sgDiv);
      this.lkDiv = DOM.ce("div", {className:"scrlContent", id:'sgLinkDiv'});
      
      zkevt.add( obj, 'keydown', function(e){ return SuggestionsObj.onKeyPress(inst,e);}, true );

      // use closures to pass in instance and event. Add single event handler to parent div for links      
      zkevt.add(this.lkDiv, 'mouseup',   function(e){SuggestionsObj.onmouseclicksglink(inst, e);}, true);  
      zkevt.add(this.lkDiv, 'mouseover', function(e){SuggestionsObj.onMouseOverSgLink(inst, e);}, true);
      
      this.sgDiv.appendChild(this.lkDiv);
      scb.parentNode.removeChild(scb);
      sgDiv.parentNode.appendChild(scb);
   }

   ceStl = this.sgDiv.style;
   ceStl.left      = pos.x + "px";
   ceStl.top       = ( pos.y + obj.offsetHeight + 2 ) + "px";
   ceStl.width     = obj.offsetWidth - 12 + "px";
   ceStl.maxHeight = MAX_HEIGHT + "px";
   this.lkDiv.style.width = obj.offsetWidth - scb.offsetWidth + 'px';
   
   this.cleanSgDiv();
   this.divLinks = new Array(valArray.length);

   
   // create document fragment to build suggestion div in
   frag = cdf();
       
   // ajax returns response as an aray of 2 element arrays - ["Jessop T15(Jessop
   // Steel)","4620"]
   // steelname(standard/maker) and rowid in name records table.
   var l = valArray.length,
       i;
   for ( i = 0; i<l; i++ )
   {
      linky = DOM.ce("a", {href:"#",id:i});
      linky.innerHTML = valArray[i][0];
      frag.appendChild(linky);
      this.divLinks[i] = linky;
   }

   this.lkDiv.appendChild(frag);
   
   if (this.lkDiv.offsetHeight > MAX_HEIGHT)
      ceStl.height = MAX_HEIGHT + "px";
   else
      ceStl.height = this.lkDiv.offsetHeight + "px";

   ceStl.visibility = "visible";
   
   scStl = scb.style; 
   scStl.top = this.sgDiv.offsetTop + 'px';
   scStl.left = this.sgDiv.offsetLeft + this.lkDiv.offsetWidth + 'px';
   scStl.height = this.sgDiv.offsetHeight + 'px';
   
   this.scroller  = new jsScrlObj(this.sgDiv, this.sgDiv.offsetWidth, this.sgDiv.offsetHeight);
   this.scrollbar = new jsScrlBar (scb, this.scroller, true, null);
   zkevt.add(doc, 'mouseup', hideSuggestions, false);
};


// override original suggest set handler. we need to apply selected value to the
// existing string,
// but before that we have to strip the string until last comma.
SuggestionsObj.prototype.setSelected = function()
{

	if (this.divLinks !== null && this.curSel >= 0) {
      var lo = this.divLinks[this.curSel],
          st = lk2SgV( lo.innerText || lo.textContent),
          suggestElem = this.sgElem,
          val, lastComa;
      
      if ( suggestElem.value.length === 0)
         suggestElem.value = st;
      else
      {
         val = suggestElem.value;
         lastComa = val.lastIndexOf(',');
         if (lastComa !== -1)
         {
            val = val.substring(0,lastComa+1);
            suggestElem.value = val + st;
         }
         else
            suggestElem.value = st;
      }
      
      // instead of simply pushing nrid, first check, for which name position
		// are we adding rowid, if that position already has id,
      // replace it with the new one, happens in cases when name is same, but
		// rowid is different.
      var numNames = suggestElem.value.split(',').length-1,
        gctlNRids = GraphCtl.nrIds,
        len = gctlNRids.length,
        posExists = false, i;

      // find out if we have a record in nrids already for that name position
      for ( i = 0; i < len; i++ )
      {
         if ( gctlNRids[i] && gctlNRids[i].namePos === numNames )
         {
            gctlNRids[i] = {name:this.nrIds[this.curSel][0], nid:this.nrIds[this.curSel][1], namePos:numNames};
            posExists = true;
         }
      }
      
      if ( posExists === false )
         gctlNRids.push( {name:this.nrIds[this.curSel][0], nid:this.nrIds[this.curSel][1], namePos:numNames} );

      // add coma after new entry and set focus on edit control
      suggestElem.value += ',';
      suggestElem.focus();
      
      this.nrIds = null;
   }
   this.hide();
};


GraphCtl.init();
