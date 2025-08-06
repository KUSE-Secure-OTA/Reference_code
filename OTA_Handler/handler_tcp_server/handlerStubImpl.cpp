#include "handlerStubImpl.hpp"
#include <iomanip>  // std::hex, std::setw
#include <openssl/cmac.h>
#include <openssl/evp.h>
#include <openssl/crypto.h>

using namespace v0::commonapi;
using json = nlohmann::json;

int chunkSize = 40000;
handlerStubImpl::handlerStubImpl() : downloadStarted_(false){
    std::cout << "[Server] HandlerStubImpl called.\n";
    //read undone stauts file
    if (!std::filesystem::exists(statusFilePath_)){
        std::ofstream create_file(statusFilePath_);
        create_file << "status=0"<<std::endl;
        create_file.close();
    }else{
        std::ifstream file(statusFilePath_);
        std::string line;
        while(std::getline(file, line)){
            if(line.rfind("status=",0)==0){
                status_ = std::stoi(line.substr(7));
                break;
            }
        }
        file.close();
    }
}

handlerStubImpl::~handlerStubImpl(){
    
}

CommonAPI::ByteBuffer handlerStubImpl::calculate_cmac(const uint8_t* data, size_t data_len) {
    CommonAPI::ByteBuffer mac_buffer;
    
    EVP_MAC* mac = EVP_MAC_fetch(NULL, "CMAC", NULL);
    if (!mac) return mac_buffer;

    EVP_MAC_CTX* ctx = EVP_MAC_CTX_new(mac);
    if(!ctx) {
        EVP_MAC_free(mac);
        return mac_buffer;
    }

    int8_t key[16] = {
        0x00, 0x01, 0x02, 0x03,
        0x04, 0x05, 0x06, 0x07,
        0x08, 0x09, 0x0A, 0x0B,
        0x0C, 0x0D, 0x0E, 0x0F
    };

    OSSL_PARAM params[] = {
        OSSL_PARAM_construct_utf8_string("cipher", (char*)"AES-128-CBC", 0),
        OSSL_PARAM_construct_octet_string("key", (void*)key, sizeof(key)),
        OSSL_PARAM_END
    };

    //const EVP_CIPHER* cipher = EVP_aes_128_cbc();

    unsigned char mac_tmp[EVP_MAX_BLOCK_LENGTH];
    size_t mac_len = 0;

    if (EVP_MAC_init(ctx, NULL, 0, params) &&
        EVP_MAC_update(ctx, reinterpret_cast<const unsigned char*>(data), data_len) &&
        EVP_MAC_final(ctx, mac_tmp, &mac_len, sizeof(mac_tmp))) {
            mac_buffer.assign(mac_tmp, mac_tmp + mac_len);
        }

    EVP_MAC_CTX_free(ctx);
    EVP_MAC_free(mac);
    return mac_buffer;
}

bool handlerStubImpl::verify_message(const uint8_t* data, size_t data_len, const CommonAPI::ByteBuffer& expected_mac) {
    CommonAPI::ByteBuffer calculated_mac = calculate_cmac(data, data_len);

    if (calculated_mac.size() != expected_mac.size()) return false;
    return CRYPTO_memcmp(calculated_mac.data(), expected_mac.data(), expected_mac.size()) == 0;
}

void handlerStubImpl::saveStatus(){
    std::ofstream file(statusFilePath_);
    file<<"status="<<status_<<std::endl;
    file.close();
}


void handlerStubImpl::updateMsg(const std::shared_ptr<CommonAPI::ClientId> _client, const CommonAPI::ByteBuffer udsMsg, updateMsgReply_t _reply) {
    if (udsMsg.empty()) {
        std::cout << "Empty Message";
        return;
        //response = {0x7F, 0x00, 0x11};
    }
    CommonAPI::ByteBuffer response;

    uint8_t serviceID = static_cast<uint8_t>(udsMsg[0]);
    std::cout << "Received service ID: 0x" << std::hex << static_cast<int>(serviceID) << std::dec << std::endl;

    switch (serviceID) {
        case 0x33: {
            std::cout << "Start download...\n";
            setStatus(static_cast<int32_t>(HandlerStatus::INIT));
            response = {0x73};
            break;
        }

        case 0x34: {
            std::cout << "[RequestDownload] Initializing download...\n";

            // std::filesystem::path filePath = "/tmp/ota_firmware.bin";
            // firmwareFile_.open(filePath, std::ios::binary | std::ios::out);
            // if (!firmwareFile.is_open()) {
            //     std::cerr << "Failed to open file for writing.\n";
            //     response = {0x7F, serviceID, 0x11};
            //     break;
            // }


            // updateFile_.open("./handler_tcp_server/received_update", std::ios::binary | std::ios::app);
            // if (!updateFile_) {
            //     std::cerr << "Fail to create new file" << std::endl;
            //     response = {0x7F, serviceID, 0x11};
            // }

            // if (updateFile_.is_open()) {
            //     updateFile_.close();
            // }
            std::string jsonStr = std::string(udsMsg.begin() + 1,udsMsg.end());
            json j = json::parse(jsonStr);
            std::ofstream out("./handler_tcp_server/tmp/received.json");
            out <<j.dump(4);
            out.close();
            downloadStarted_ = true;
            setStatus(static_cast<int32_t>(HandlerStatus::WAIT));
            //change
            response = {0x74};
            break;
        }

        case 0x36: {
            // Start Installation
            setStatus(static_cast<int32_t>(HandlerStatus::PROCESSING));
            
            // Read udsRequest message
            int32_t n = udsMsg[2];
            int8_t fileNameLength = static_cast<int8_t>(udsMsg[3]);
            std::cout << "current file length:" << fileNameLength<< std::endl;
            std::string fileName = std::string(udsMsg.begin() + 4,udsMsg.begin() + fileNameLength + 4);
            std::cout << "current file name:" << fileName << std::endl;
            std::cout<<"# of chunks: "<<n<<std::endl;

            // Verify chunk
            CommonAPI::ByteBuffer chunk(udsMsg.begin() + 4 + fileNameLength, udsMsg.begin() + 4 + fileNameLength + chunkSize);
            CommonAPI::ByteBuffer mac(udsMsg.begin() + 4 + fileNameLength + chunkSize, udsMsg.end());
            size_t msgLen = sizeof(chunk);
            size_t mac_len = sizeof(mac);
            
            CommonAPI::ByteBuffer cmac = calculate_cmac(chunk.data(), msgLen);

            if(!verify_message(chunk.data(), msgLen, cmac)) {
                std::cerr << "\n\n\t\tVerify fail\n" << std::endl;
                response = {0x7F, serviceID, 0x11};
                break;
            }
            else {
                std::cout << "\n\n\t\tSuccess CMAC Verification\n" << std::endl;
            }
            int padLen = chunk[7998] | (static_cast<uint8_t>(chunk[7999])<<8);
            // std::cout << "chunk[7998]=" <<static_cast<int>(chunk[7998])<<std::endl;
            // std::cout << "chunk[7999]=" <<static_cast<int>(chunk[7999])<<std::endl;

            //int padLen = static_cast<int>(chunk.back());
            std::cout << "pad len :" <<padLen<< std::endl;
            if (padLen == 0 || padLen > chunkSize || padLen > chunk.size()) {
                std::cerr << "[ERROR] Incorrect chunk" << std::endl;
            }

            for (size_t i = chunk.size() - padLen; i < chunk.size() -2; i++) {
                if (chunk[i] != 0xFF) {
                    std::cerr << "Not padded message" << std::endl;
                    break;
                }
                if (i == chunk.size() - 3){
                    chunk.erase(chunk.begin() + chunk.size() - padLen, chunk.end());
                }
            }
            std::cout <<"after remove padding "<<chunk.size()<<std::endl;
            CommonAPI::ByteBuffer file(chunk.begin(), chunk.end());
            fileName = "./handler_tcp_server/tmp/" + fileName;
            updateFile_.open(fileName, std::ios::binary | std::ios::app);

            // Write file
            try {
                if (updateFile_.is_open()) {
                    std::cout << "chunk size :" <<file.size() <<std::endl;
                    updateFile_.write(reinterpret_cast<const char*>(file.data()), file.size());
                }
                else {
                    std::cerr << "File is not open" << std::endl;
                    response = {0x7F, serviceID, 0x11};
                    break;
                }
            }
            catch (const std::exception& e) {
                std::cerr << "Fail to save update file" << std::endl;
                response = {0x7F, serviceID, 0x11};
                break;
            }
            if (updateFile_.is_open()) {
                updateFile_.close();
                std::cout<<"file:"<<fileName<<" chunk # "<<n<<"is closed"<<std::endl;
            }else{
                std::cout<<"nothing to close"<<std::endl;
            }
            // if (!downloadStarted_ || !firmwareFile_.is_open()) {
            //     std::cerr << "TransferData called before RequestDownload.\n";
            //     response = {0x7F, serviceID, 0x11};
            //     break;
            // }

            //firmwareFile_.write(reinterpret_cast<const char*>(&udsRequest[1]), udsRequest.size() - 1);
            //setStatus(static_cast<int32_t>(HandlerStatus::WAIT));

            // Se udsResponse message
            response = {0x76, static_cast<uint8_t>(n+1)}; //0x76, iter
            // save undone status file
            break;
        }

        case 0x37: {
            std::cout << "[TransferExit] Finalizing firmware transfer.\n";
            // if (firmwareFile_.is_open()) {
            //     firmwareFile_.close();
            // }
            // del undone undone status file

            // if (updateFile_.is_open()) {
            //     updateFile_.close();
            // }

            downloadStarted_ = false;
            setStatus(static_cast<int32_t>(HandlerStatus::VERIFY));
            
            // Process the verification

            // move file
            std::ifstream file("./handler_tcp_server/tmp/received.json",std::ios::binary);
            json j;
            if(!file.is_open()){
                std::cerr << "cannot open list.json" <<std::endl;
                break;
            }
            try{
                file >> j;
                file.close();
            }catch(json::parse_error& e){
                std::cerr << "json parsing error: " <<e.what() << std::endl;
                break;
            }                
            std::filesystem::path baseDir = std::filesystem::current_path();
            std::filesystem::path interDir = "handler_tcp_server/tmp";
            std::string targetDir = extractDirFromJson("./boot_manager/status.json", 4);
            std::string targetDirPath = "";

            baseDir = baseDir / interDir;
            if(j.contains("files")&&j["files"].is_array()){
                for(auto& file : j["files"]){
                    std::string filename = file.value("name", "");
                    if (filename.empty()){
                        std::cerr << "%%%%% Empty File Name %%%%%" <<std::endl;
                        continue;
                    }
                    std::filesystem::path filePath = baseDir / filename;
                    targetDirPath = "./boot_manager/" + targetDir +"/"+ filename;
                    moveFile(filePath.string(),targetDirPath);
                    targetDirPath = "";
                }
                setStatus(static_cast<int32_t>(HandlerStatus::READY));
                response = {0x77};
                break;
            }else{
                std::cerr<<"[error] empty list json error"<<std::endl;
            }

        }

        default:
            std::cerr << "Unsupported service ID: " << static_cast<int>(serviceID) << std::endl;
            response = {0x7F, serviceID, 0x11};
            break;
    }

    _reply(response);
    if (getStatus() == static_cast<int32_t>(HandlerStatus::PROCESSING)) setStatus(static_cast<int32_t>(HandlerStatus::WAIT));
}

// void handlerStubImpl::pushUpdate(const std::shared_ptr<CommonAPI::ClientId> _client, 
//             const CommonAPI::ByteBuffer _firmware, const CommonAPI::ByteBuffer _signature, pushUpdateReply_t _reply){
//     std::ofstream firmwareFile("./handler_tcp_server/received_update", std::ios::binary | std::ios::out);
//     std::ofstream signatureFile("./handler_tcp_server/received_signature", std::ios::binary | std::ios::out);
//     if (!firmwareFile) {
//         std::cerr << "Failed to create Firmware\n";
//         _reply(-1);
//         return;
//     }
//     if (!signatureFile) {
//         std::cerr << "Failed to verify signature\n";
//         firmwareFile.close();
//         _reply(-1);
//         return;
//     }
//     // Save firmware and signature
//     try{
//         firmwareFile.write(reinterpret_cast<const char*>(_firmware.data()), _firmware.size());
//         signatureFile.write(reinterpret_cast<const char*>(_signature.data()), _signature.size());
//         firmwareFile.close();
//         signatureFile.close();
//     }
//     catch (const std::exception& e) {
//         std::cerr << "Error in saving process: " << e.what() << "\n";
//         firmwareFile.close();
//         signatureFile.close();
//         _reply(-1);
//         return;
//     }
//     std::cout << "Complete saving (" << _firmware.size() << " bytes, " << _signature.size() << " bytes)\n";
//     _reply(1);
// }

void handlerStubImpl::notifyHandlerStatus(const std::shared_ptr<CommonAPI::ClientId> _client, const int32_t& statusCode) {
    std::cout << "[Server] Broadcasting status: " << statusCode << std::endl;

    fireHandlerStatusEvent(statusCode);
}