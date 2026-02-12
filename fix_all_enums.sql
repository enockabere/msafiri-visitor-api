-- Fix all enum types to support both lowercase and uppercase values
-- This is needed because SQLAlchemy converts enum values to uppercase

-- travelertype
ALTER TYPE travelertype ADD VALUE IF NOT EXISTS 'SELF';
ALTER TYPE travelertype ADD VALUE IF NOT EXISTS 'DEPENDANT';
ALTER TYPE travelertype ADD VALUE IF NOT EXISTS 'STAFF';

-- traveleracceptancestatus
ALTER TYPE traveleracceptancestatus ADD VALUE IF NOT EXISTS 'PENDING';
ALTER TYPE traveleracceptancestatus ADD VALUE IF NOT EXISTS 'ACCEPTED';
ALTER TYPE traveleracceptancestatus ADD VALUE IF NOT EXISTS 'DECLINED';

-- approvalactiontype
ALTER TYPE approvalactiontype ADD VALUE IF NOT EXISTS 'APPROVED';
ALTER TYPE approvalactiontype ADD VALUE IF NOT EXISTS 'REJECTED';

-- documenttype
ALTER TYPE documenttype ADD VALUE IF NOT EXISTS 'TICKET';
ALTER TYPE documenttype ADD VALUE IF NOT EXISTS 'ITINERARY';
ALTER TYPE documenttype ADD VALUE IF NOT EXISTS 'BOARDING_PASS';
ALTER TYPE documenttype ADD VALUE IF NOT EXISTS 'OTHER';

-- dependantrelationship
ALTER TYPE dependantrelationship ADD VALUE IF NOT EXISTS 'SPOUSE';
ALTER TYPE dependantrelationship ADD VALUE IF NOT EXISTS 'CHILD';
ALTER TYPE dependantrelationship ADD VALUE IF NOT EXISTS 'PARENT';
ALTER TYPE dependantrelationship ADD VALUE IF NOT EXISTS 'SIBLING';
ALTER TYPE dependantrelationship ADD VALUE IF NOT EXISTS 'OTHER';
