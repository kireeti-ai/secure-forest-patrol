#include "RfidReader.h"

#include <MFRC522.h>
#include <SPI.h>

namespace
{
    MFRC522 *reader = nullptr;
}

namespace forest::sensors
{
    bool RfidReader::begin(int sckPin, int misoPin, int mosiPin, int chipSelectPin, int resetPin)
    {
        chipSelectPin_ = chipSelectPin;
        resetPin_ = resetPin;
        SPI.begin(sckPin, misoPin, mosiPin, chipSelectPin_);
        reader = new MFRC522(chipSelectPin_, resetPin_);
        reader->PCD_Init(chipSelectPin_, resetPin_);
        initialized_ = reader->PCD_PerformSelfTest();
        reader->PCD_Init(chipSelectPin_, resetPin_);
        return initialized_;
    }

    bool RfidReader::readUid(std::array<std::uint8_t, 10> &uid, std::size_t &uidSize)
    {
        uidSize = 0U;
        if (!initialized_ || reader == nullptr || !reader->PICC_IsNewCardPresent() || !reader->PICC_ReadCardSerial())
        {
            return false;
        }

        uidSize = reader->uid.size;
        if (uidSize == 0U || uidSize > uid.size())
        {
            reader->PICC_HaltA();
            reader->PCD_StopCrypto1();
            uidSize = 0U;
            return false;
        }

        for (std::size_t index = 0U; index < uidSize; ++index)
        {
            uid[index] = reader->uid.uidByte[index];
        }
        reader->PICC_HaltA();
        reader->PCD_StopCrypto1();
        return true;
    }
} // namespace forest::sensors
