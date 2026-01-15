-- Migration: Remove ® (registered trademark) symbol from all grade names
-- Date: 2026-01-15
-- Reason: Improve search usability - users can't easily type ® symbol
--
-- Affected grades (15 total):
-- - AL-6XN®, Nimonic® 75/80A/90, Nitronic® 50
-- - Alleima® 253 MA/2RE10/2RE69/353 MA/3RE60
-- - E-BRITE®, SEA-CURE®, SHOMAC® 30-2
-- - Safurex®, Sanicro® 25

-- Check affected grades before update
SELECT 'Before update - grades with ® symbol:' AS info;
SELECT grade FROM steel_grades WHERE grade LIKE '%®%' ORDER BY grade;

-- Remove ® symbol from all grade names
UPDATE steel_grades
SET grade = REPLACE(grade, '®', '')
WHERE grade LIKE '%®%';

-- Verify update
SELECT 'After update - grades with ® symbol (should be 0):' AS info;
SELECT COUNT(*) AS remaining_count FROM steel_grades WHERE grade LIKE '%®%';

-- Show updated grades
SELECT 'Updated grades (sample):' AS info;
SELECT grade FROM steel_grades
WHERE grade IN (
    'AL-6XN', 'Nimonic 75', 'Nimonic 80A', 'Nimonic 90', 'Nitronic 50',
    'Alleima 253 MA', 'E-BRITE', 'SEA-CURE', 'SHOMAC 30-2', 'Safurex', 'Sanicro 25'
)
ORDER BY grade;
