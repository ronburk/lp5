# Main pane resizing checks

Open the project in the browser and confirm the Navigation, Source, and Output
panes are separated by two visible, full-height resize handles.

1. Drag the first handle left and right. Navigation and Source should change
   width together while Output keeps its width. Drag the second handle and
   confirm Source and Output change while Navigation keeps its width.
2. Confirm each pane stops at its minimum width: 120 px for Navigation, 200 px
   for Source, and 160 px for Output. At a narrow viewport, horizontal overflow
   is acceptable once the combined minimum pane widths no longer fit.
3. Tab to each handle. Left/Right arrows should adjust its adjacent panes by
   10 px; Shift+Left/Right should adjust by 40 px. Home and End should move the
   handle to the corresponding minimum/maximum position. Screen readers should
   identify each control as a vertical separator with its current value.
4. Resize the browser after dragging. The panes should keep their adjusted
   proportions, with both handles remaining usable and aligned to the panes.
5. Confirm scrolling and editing within each pane still work, and clicking or
   selecting article text away from a handle behaves as before. Reloading should
   restore the default 25/37.5/37.5 pane proportions.
